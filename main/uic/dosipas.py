import typing
import pathlib
import asn1tools
import dataclasses
import datetime
import pytz
import cryptography.exceptions
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.asymmetric.dsa
import cryptography.hazmat.primitives.asymmetric.ec
import cryptography.hazmat.primitives.serialization
from . import certs, util

ROOT = pathlib.Path(__file__).parent
ASN1_SPEC_V1 = asn1tools.compile_files([ROOT / "asn1" / "uicBarcodeHeader_v1.0.0.asn"], codec="uper")
ASN1_SPEC_V2 = asn1tools.compile_files([ROOT / "asn1" / "uicBarcodeHeader_v2.0.1.asn"], codec="uper")
ASN1_DCD_SPEC_V1 = asn1tools.compile_files([ROOT / "asn1" / "uicDynamicContentData_v1.0.3.asn"], codec="uper")


@dataclasses.dataclass
class DOSIPASEnvelope:
    version: int
    level_2_data: typing.Dict
    level_1_signed_data: bytes = b""
    level_1_signature: typing.Optional[bytes] = None
    level_2_signed_data: bytes = b""
    level_2_signature: typing.Optional[bytes] = None
    level_2_public_key: typing.Optional[bytes] = None
    level_2_record: typing.Optional["Record"] = None
    records: typing.List["Record"] = dataclasses.field(default_factory=list)
    expiry: typing.Optional[datetime.datetime] = None

    def signing_cert(self):
        return certs.signing_cert(
            self.level_2_data["level1Data"]["securityProviderNum"],
            self.level_2_data["level1Data"]["keyId"]
        )

    def can_verify(self):
        if "level1SigningAlg" not in self.level_2_data["level1Data"]:
            return False

        return bool(certs.public_key(
            self.level_2_data["level1Data"]["securityProviderNum"],
            self.level_2_data["level1Data"]["keyId"]
        ))

    def verify_level_1_signature(self):
        if not self.level_1_signature or not self.level_1_signed_data:
            return False

        pk = certs.public_key(
            self.level_2_data["level1Data"]["securityProviderNum"],
            self.level_2_data["level1Data"]["keyId"]
        )
        if not pk:
            return False

        sig_alg = self.level_2_data["level1Data"].get("level1SigningAlg")

        if sig_alg == "2.16.840.1.101.3.4.3.1":
            if not isinstance(pk, cryptography.hazmat.primitives.asymmetric.dsa.DSAPublicKey):
                return False

            hasher = cryptography.hazmat.primitives.hashes.SHA224()
        elif sig_alg == "2.16.840.1.101.3.4.3.2":
            if not isinstance(pk, cryptography.hazmat.primitives.asymmetric.dsa.DSAPublicKey):
                return False

            hasher = cryptography.hazmat.primitives.hashes.SHA256()
        elif sig_alg == "1.2.840.10045.4.3.2":
            if not isinstance(pk, cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePublicKey):
                return False

            hasher = cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                cryptography.hazmat.primitives.hashes.SHA256()
            )
        else:
            return False

        try:
            pk.verify(self.level_1_signature, self.level_1_signed_data, hasher)
            return True
        except cryptography.exceptions.InvalidSignature:
            return False

    def verify_level_2_signature(self):
        if not self.level_2_signature or not self.level_2_signed_data or "level2SigningAlg" not in self.level_2_data["level1Data"]:
            return False

        sig_alg = self.level_2_data["level1Data"].get("level2SigningAlg")

        if sig_alg == "2.16.840.1.101.3.4.3.1":
            try:
                pk = cryptography.hazmat.primitives.serialization.load_der_public_key(self.level_2_public_key)
            except ValueError:
                return False

            if not isinstance(pk, cryptography.hazmat.primitives.asymmetric.dsa.DSAPublicKey):
                return False

            hasher = cryptography.hazmat.primitives.hashes.SHA224()
        elif sig_alg == "2.16.840.1.101.3.4.3.2":
            try:
                pk = cryptography.hazmat.primitives.serialization.load_der_public_key(self.level_2_public_key)
            except ValueError:
                return False

            if not isinstance(pk, cryptography.hazmat.primitives.asymmetric.dsa.DSAPublicKey):
                return False

            hasher = cryptography.hazmat.primitives.hashes.SHA256()
        elif sig_alg == "1.2.840.10045.4.3.2":
            try:
                pk = cryptography.hazmat.primitives.serialization.load_der_public_key(self.level_2_public_key)
            except ValueError:
                pk_oid = self.level_2_data["level1Data"].get("level2KeyAlg")
                if pk_oid == "1.2.840.10045.3.1.7":
                    curve = cryptography.hazmat.primitives.asymmetric.ec.SECP256R1()
                else:
                    return False

                try:
                    pk = cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePublicKey.from_encoded_point(
                        curve,
                        self.level_2_public_key
                    )
                except ValueError:
                    return False

            if not isinstance(pk, cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePublicKey):
                return False

            hasher = cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                cryptography.hazmat.primitives.hashes.SHA256()
            )
        else:
            return False

        try:
            pk.verify(self.level_2_signature, self.level_2_signed_data, hasher)
            return True
        except cryptography.exceptions.InvalidSignature:
            return False

    @classmethod
    def decode(cls, envelope: bytes) -> typing.Optional["DOSIPASEnvelope"]:
        out = None
        try:
            data = ASN1_SPEC_V2.decode("UicBarcodeHeader", envelope)
            if data["format"] == "U2":
                out = cls(
                    version=2,
                    level_2_data=data["level2SignedData"],
                    level_2_signed_data=ASN1_SPEC_V2.encode("Level2DataType", data["level2SignedData"]),
                    level_2_signature=data.get("level2Signature"),
                    level_1_signed_data=ASN1_SPEC_V2.encode("Level1DataType", data["level2SignedData"]["level1Data"]),
                    level_1_signature=data["level2SignedData"]["level1Signature"],
                    level_2_public_key=data["level2SignedData"]["level1Data"].get("level2PublicKey"),
                )
        except asn1tools.DecodeError:
            pass

        try:
            data = ASN1_SPEC_V1.decode("UicBarcodeHeader", envelope)
            if data["format"] == "U1":
                out = cls(
                    version=1,
                    level_2_data=data["level2SignedData"],
                    level_2_signed_data=ASN1_SPEC_V1.encode("Level2DataType", data["level2SignedData"]),
                    level_2_signature=data.get("level2Signature"),
                    level_1_signed_data=ASN1_SPEC_V1.encode("Level1DataType", data["level2SignedData"]["level1Data"]),
                    level_1_signature=data["level2SignedData"]["level1Signature"],
                    level_2_public_key=data["level2SignedData"]["level1Data"].get("level2PublicKey"),
                )
        except asn1tools.DecodeError:
            pass

        if out:
            if d := out.level_2_data.get("level2Data"):
                out.level_2_record = Record(
                    format=d["dataFormat"],
                    data=d["data"],
                )

            for r in out.level_2_data["level1Data"]["dataSequence"]:
                out.records.append(Record(
                    format=r["dataFormat"],
                    data=r["data"],
                ))

            if out.level_2_data["level1Data"].get("endOfValidityYear"):
                year = out.level_2_data["level1Data"]["endOfValidityYear"]
                day = out.level_2_data["level1Data"]["endOfValidityDay"]
                time = out.level_2_data["level1Data"]["endOfValidityTime"]

                expiry = datetime.datetime(year=year, month=1, day=1)
                expiry += datetime.timedelta(days=day - 1)
                expiry += datetime.timedelta(minutes=time)
                out.expiry = pytz.utc.localize(expiry)

            return out

        return None


@dataclasses.dataclass
class Record:
    format: str
    data: bytes


@dataclasses.dataclass
class DCD:
    version: int
    data: typing.Dict[str, typing.Any]

    @classmethod
    def parse(cls, version: int, data: bytes) -> "DCD":
        try:
            if version == 1:
                return cls(
                    version=version,
                    data=ASN1_DCD_SPEC_V1.decode("UicDynamicContentData", data)
                )
            else:
                raise util.UICException("Unsupported UIC dynamic data version")
        except asn1tools.DecodeError as e:
            raise util.UICException("Failed to decode UIC dynamic data") from e
