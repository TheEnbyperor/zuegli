import dataclasses
import typing
import ber_tlv.tlv
from . import pki, util, iso9796


@dataclasses.dataclass
class Authorization:
    signature: bytes
    residual_data: bytes

    def decrypt_with_cert(self, cert: pki.CertificateData) -> bytes:
        return iso9796.decrypt_with_cert(self.signature, self.residual_data, cert)

@dataclasses.dataclass
class EnvelopeV2:
    authorizations: typing.List[Authorization]
    certificate: pki.Certificate
    ca_reference: pki.CAReference

    @classmethod
    def parse(cls, data: bytes) -> "EnvelopeV2":
        try:
            elms = ber_tlv.tlv.Tlv.Parser.parse(data, False, [], False, 0)
        except Exception as e:
            raise util.VDVException("Failed to parse envelope, invalid BER-TLV") from e

        signature = None
        residual_data = None
        certificate = None
        ca_reference = None
        multiple_authorizations = None

        for tag, data in elms:
            if tag == util.TAG_MULTIPLE_AUTHORIZATIONS:
                multiple_authorizations = []
                try:
                    elms = ber_tlv.tlv.Tlv.Parser.parse(data, False, [], False, 0)
                except Exception as e:
                    raise util.VDVException("Failed to parse envelope, invalid BER-TLV") from e

                if elms[0][0] != util.TAG_NUMBER_AUTHORIZATIONS:
                    raise util.VDVException("Missing authorization count")
                if len(elms[0][1]) != 1:
                    raise util.VDVException("Invalid authorization count length")
                authorization_count = int.from_bytes(elms[0][1], "big")

                for i in range(0, authorization_count * 2, 2):
                    if elms[i+1][0] != util.TAG_SIGNATURE:
                        raise util.VDVException("Missing signature")
                    if len(elms[i+1][1]) != 128:
                        raise util.VDVException("Invalid signature length")
                    signature = elms[i+1][1]
                    if elms[i+2][0] != util.REMAINING_DATA:
                        raise util.VDVException("Missing remaining data")
                    residual_data = elms[i+2][1]

                    multiple_authorizations.append(Authorization(signature, residual_data))

                i = (authorization_count * 2) + 1

                if elms[i][0] != util.TAG_CERTIFICATE:
                    raise util.VDVException("Missing certificate")
                certificate = pki.Certificate.parse_tags(elms[i][1])

                if elms[i+1][0] != util.TAG_CA_REFERENCE:
                    raise util.VDVException("Missing CA reference")
                if len(elms[i+1][1]) != 8:
                    raise util.VDVException("Invalid CA reference length")
                ca_reference = pki.CAReference.from_bytes(elms[i+1][1])

            elif tag == util.TAG_SIGNATURE:
                if len(data) != 128:
                    raise util.VDVException("Invalid signature length")
                if signature:
                    raise util.VDVException("Multiple signatures")
                if multiple_authorizations:
                    raise util.VDVException("Combined single and multiple authorizations")
                signature = data

            elif tag == util.REMAINING_DATA:
                if residual_data:
                    raise util.VDVException("Multiple residual signature data")
                if multiple_authorizations:
                    raise util.VDVException("Combined single and multiple authorizations")
                residual_data = data

            elif tag == util.TAG_CERTIFICATE:
                if certificate:
                    raise util.VDVException("Multiple certificates")
                if multiple_authorizations:
                    raise util.VDVException("Combined single and multiple authorizations")
                certificate = pki.Certificate.parse_tags(data)

            elif tag == util.TAG_CA_REFERENCE:
                if len(data) != 8:
                    raise util.VDVException("Invalid certification authority reference length")
                if ca_reference:
                    raise util.VDVException("Multiple certification authority references")
                if multiple_authorizations:
                    raise util.VDVException("Combined single and multiple authorizations")
                ca_reference = pki.CAReference.from_bytes(data)

            else:
                raise util.VDVException(f"Unknown tag: 0x{tag:02X}")

        if not multiple_authorizations:
            if not signature:
                raise util.VDVException("No signature")
            if not residual_data:
                raise util.VDVException("No residual signature data")
            multiple_authorizations = [Authorization(signature, residual_data)]
        if not certificate:
            raise util.VDVException("No CV certificate")
        if not ca_reference:
            raise util.VDVException("No certification authority reference")

        return cls(
            authorizations=multiple_authorizations,
            certificate=certificate,
            ca_reference=ca_reference,
        )