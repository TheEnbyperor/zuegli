import hashlib
import json
import typing
import zipfile
import io
import datetime
import asn1crypto.core
import asn1crypto.algos
import asn1crypto.cms
import asn1crypto.tsp
import asn1crypto.x509
import cryptography.x509.extensions
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.asymmetric.padding
import cryptography.hazmat.primitives.asymmetric.dsa
import cryptography.hazmat.primitives.asymmetric.ec
import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.primitives.serialization.pkcs7
import niquests
from django.conf import settings

TSP_URL = "http://timestamp.apple.com/ts01"
TSP_CLIENT = niquests.Session(happy_eyeballs=True)

class PKPass:
    def __init__(self):
        self.data = {}
        self.manifest = {}
        self.signature = None

    def add_file(self, filename: str, data: bytes):
        file_hash = hashlib.sha1(data).hexdigest()
        self.data[filename] = data
        self.manifest[filename] = file_hash

    def sign(self):
        manifest = json.dumps(self.manifest).encode("utf-8")
        self.data["manifest.json"] = manifest
        manifest_digest = cryptography.hazmat.primitives.hashes.Hash(
            cryptography.hazmat.primitives.hashes.SHA512()
        )
        manifest_digest.update(manifest)
        manifest_digest = manifest_digest.finalize()
        if isinstance(settings.PKPASS_KEY, cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey):
            signature_alg = asn1crypto.algos.SignedDigestAlgorithmId("rsassa_pkcs1v15")
        elif isinstance(settings.PKPASS_KEY, cryptography.hazmat.primitives.asymmetric.dsa.DSAPrivateKey):
            signature_alg = asn1crypto.algos.SignedDigestAlgorithmId("dsa")
        elif isinstance(settings.PKPASS_KEY, cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePrivateKey):
            signature_alg = asn1crypto.algos.SignedDigestAlgorithmId("ecdsa")
        else:
            raise ValueError("Unsupported private key type")

        signed_attrs = asn1crypto.cms.CMSAttributes([
            asn1crypto.cms.CMSAttribute({
                "type": asn1crypto.cms.CMSAttributeType("content_type"),
                "values": [asn1crypto.cms.ContentType("data")]
            }),
            asn1crypto.cms.CMSAttribute({
                "type": asn1crypto.cms.CMSAttributeType("signing_time"),
                "values": [asn1crypto.core.UTCTime(datetime.datetime.now(datetime.UTC))]
            }),
            asn1crypto.cms.CMSAttribute({
                "type": asn1crypto.cms.CMSAttributeType("message_digest"),
                "values": [asn1crypto.core.OctetString(manifest_digest)]
            })
        ])
        if isinstance(settings.PKPASS_KEY, cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey):
            signature = settings.PKPASS_KEY.sign(
                signed_attrs.dump(),
                cryptography.hazmat.primitives.asymmetric.padding.PKCS1v15(),
                cryptography.hazmat.primitives.hashes.SHA512()
            )
        elif isinstance(settings.PKPASS_KEY, cryptography.hazmat.primitives.asymmetric.dsa.DSAPrivateKey):
            signature = settings.PKPASS_KEY.sign(
                signed_attrs.dump(),
                cryptography.hazmat.primitives.hashes.SHA512()
            )
        elif isinstance(settings.PKPASS_KEY, cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePrivateKey):
            signature = settings.PKPASS_KEY.sign(
                signed_attrs.dump(),
                cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                    cryptography.hazmat.primitives.hashes.SHA512()
                )
            )

        timestamp_nonce = int.from_bytes(secrets.token_bytes(8), "big")
        timestamp_digest = cryptography.hazmat.primitives.hashes.Hash(
            cryptography.hazmat.primitives.hashes.SHA512()
        )
        timestamp_digest.update(signature)
        timestamp_digest = timestamp_digest.finalize()
        timestamp_req = asn1crypto.tsp.TimeStampReq({
            "version": asn1crypto.tsp.Version("v1"),
            "message_imprint": asn1crypto.tsp.MessageImprint({
                "hash_algorithm": asn1crypto.algos.DigestAlgorithm({"algorithm": "sha512"}),
                "hashed_message": timestamp_digest,
            }),
            "cert_req": True,
            "nonce": timestamp_nonce,
        })
        r = TSP_CLIENT.post(TSP_URL, headers={
            "Content-Type": "application/timestamp-query",
            "User-Agent": "Zuegli (q@magicalcodewit.ch)"
        }, data=timestamp_req.dump())
        r.raise_for_status()
        if r.headers["Content-Type"] != "application/timestamp-reply":
            raise ValueError("Unexpected content type reply from timestamping server")
        timestamp_resp = asn1crypto.tsp.TimeStampResp.load(r.content)
        if timestamp_resp["status"]["status"].native not in ("granted", "granted_with_mods"):
            raise ValueError(f"Error response from timestamping server: {timestamp_resp['status']['status_string']}")
        tst = timestamp_resp["time_stamp_token"]
        if tst["content_type"].native != "signed_data":
            raise ValueError(f"Unexpected content type from timestamping server: {tst['content_type']}")
        tst_signed_data = tst["content"]
        if tst_signed_data["encap_content_info"]["content_type"].native != "tst_info":
            raise ValueError(f"Unexpected content type from timestamping server: {tst_signed_data['encap_content_info']['content_type']}")
        tst_info = asn1crypto.tsp.TSTInfo.load(bytes(tst_signed_data["encap_content_info"]["content"]))
        if "nonce" not in tst_info or tst_info["nonce"].native != timestamp_nonce:
            raise ValueError("Mismatched nonce from timestamping server")

        cms_signature = asn1crypto.cms.ContentInfo({
            "content_type": asn1crypto.cms.ContentType("signed_data"),
            "content": asn1crypto.cms.SignedData({
                "version": asn1crypto.cms.CMSVersion("v1"),
                "digest_algorithms": asn1crypto.cms.DigestAlgorithms([
                    asn1crypto.algos.DigestAlgorithm({"algorithm": "sha512"})
                ]),
                "encap_content_info": asn1crypto.cms.ContentInfo({
                    "content_type": asn1crypto.cms.ContentType("data")
                }),
                "certificates": asn1crypto.cms.CertificateSet([
                    asn1crypto.cms.CertificateChoices(
                        {"certificate": asn1crypto.x509.Certificate.load(settings.WWDR_CERTIFICATE.public_bytes(
                                encoding=cryptography.hazmat.primitives.serialization.Encoding.DER))}
                    ),
                    asn1crypto.cms.CertificateChoices(
                        {"certificate": asn1crypto.x509.Certificate.load(settings.PKPASS_CERTIFICATE.public_bytes(
                                encoding=cryptography.hazmat.primitives.serialization.Encoding.DER))}
                    )
                ]),
                "signer_infos": asn1crypto.cms.SignerInfos([asn1crypto.cms.SignerInfo({
                    "version": asn1crypto.cms.CMSVersion("v3"),
                    "sid": asn1crypto.cms.SignerIdentifier({
                        "subject_key_identifier": settings.PKPASS_CERTIFICATE.extensions.get_extension_for_class(
                            cryptography.x509.extensions.SubjectKeyIdentifier).value.key_identifier,
                    }),
                    "digest_algorithm": asn1crypto.algos.DigestAlgorithm({"algorithm": "sha512"}),
                    "signed_attrs": signed_attrs,
                    "signature_algorithm": asn1crypto.algos.SignedDigestAlgorithm({
                        "algorithm": signature_alg
                    }),
                    "signature": signature,
                    "unsigned_attrs": asn1crypto.cms.CMSAttributes([
                        asn1crypto.cms.CMSAttribute({
                            "type": asn1crypto.cms.CMSAttributeType("signature_time_stamp_token"),
                            "values": [tst]
                        }),
                    ])
                })])
            })
        })
        self.data["signature"] = cms_signature.dump()

    def get_buffer(self) -> bytes:
        zip_buffer = io.BytesIO()
        zip = zipfile.ZipFile(zip_buffer, "w")
        for filename, data in self.data.items():
            zip.writestr(filename, data)
        zip.close()
        return zip_buffer.getvalue()


class MultiPKPass:
    def __init__(self):
        self.counter = 1
        self.zip_buffer = io.BytesIO()
        self.zip = zipfile.ZipFile(self.zip_buffer, "w")

    def add_pkpass(self, pkpass: typing.Union[PKPass, bytes]):
        if isinstance(pkpass, PKPass):
            self.zip.writestr(f"pass-{self.counter}.pkpass", pkpass.get_buffer())
        else:
            self.zip.writestr(f"pass-{self.counter}.pkpass", pkpass)
        self.counter += 1

    def get_buffer(self) -> bytes:
        self.zip.close()
        return self.zip_buffer.getvalue()
