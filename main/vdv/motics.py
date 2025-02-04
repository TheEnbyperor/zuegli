import dataclasses
import ber_tlv.tlv
import datetime
import typing
import cryptography.exceptions
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.asymmetric.ec

from . import util, pki, ticket

ECDSA_SHA256_OID = [1, 2, 840, 10045, 4, 3, 2]
ECDSA_SHA384_OID = [1, 2, 840, 10045, 4, 3, 3]

def oid_to_name(oid) -> str:
    if oid == ECDSA_SHA256_OID:
        return "ecdsa-with-SHA256"
    if oid == ECDSA_SHA384_OID:
        return "ecdsa-with-SHA384"
    else:
        return ".".join(list(map(str, oid)))

class NotAMoticsException(util.VDVException):
    pass

@dataclasses.dataclass
class Motics:
    identifier: str
    version: int
    random_data: typing.Optional[bytes]
    timestamp: datetime.datetime
    time_offset: typing.Optional[int]
    application_data: bytes
    signature_oid: typing.List[int]
    signature: bytes
    certificate: "pki.Certificate"
    certificate_data: "CertificateData"
    signed_data: bytes

    @classmethod
    def parse(cls, data: bytes) -> "Motics":
        try:
            elms = ber_tlv.tlv.Tlv.Parser.parse(data, False, [], False, 0)
        except Exception as e:
            raise util.VDVException("Failed to parse envelope, invalid BER-TLV") from e

        if len(elms) != 1 or elms[0][0] != util.TAG_COPY_PROTECTION_CONTAINER:
            raise NotAMoticsException()

        try:
            elms = ber_tlv.tlv.Tlv.Parser.parse(elms[0][1], False, [], False, 0)
        except Exception as e:
            raise util.VDVException("Failed to parse envelope, invalid BER-TLV") from e

        identifier = None
        version = None
        random_data = None
        timestamp = None
        time_offset = None
        application_data = None
        signature_oid = None
        signature = None
        certificate = None

        signed_elms = list(filter(lambda m: m[0] in (
            util.TAG_MOTICS_IDENTIFIER,
            util.TAG_MOTICS_VERSION,
            util.TAG_MOTICS_SE_ID,
            util.TAG_MOTICS_RANDOM_DATA,
            util.TAG_MOTICS_TIMESTAMP,
            util.TAG_MOTICS_TIME_OFFSET,
            util.TAG_MOTICS_APPLICATION_DATA,
            util.TAG_OID
        ), elms))
        signed_data = ber_tlv.tlv.Tlv.build(signed_elms)

        for tag, data in elms:
            if tag == util.TAG_MOTICS_IDENTIFIER:
                if identifier:
                    raise util.VDVException("Multiple identifiers")
                try:
                    identifier = data.decode("utf-8")
                except Exception as e:
                    raise util.VDVException("Failed to decode identifier") from e

            elif tag == util.TAG_MOTICS_VERSION:
                if version:
                    raise util.VDVException("Multiple versions")

                version = int.from_bytes(data, "big")

            elif tag == util.TAG_MOTICS_RANDOM_DATA:
                if random_data:
                    raise util.VDVException("Multiple random data")

                random_data = data

            elif tag == util.TAG_MOTICS_TIMESTAMP:
                if timestamp:
                    raise util.VDVException("Multiple timestamps")

                i = int.from_bytes(data, "big")
                timestamp = datetime.datetime.fromtimestamp(i, datetime.timezone.utc)

            elif tag == util.TAG_MOTICS_TIME_OFFSET:
                if time_offset:
                    raise util.VDVException("Multiple time offsets")

                time_offset = int.from_bytes(data, "big")

            elif tag == util.TAG_MOTICS_APPLICATION_DATA:
                if application_data:
                    raise util.VDVException("Multiple application data")

                application_data = data

            elif tag == util.TAG_OID:
                if signature_oid:
                    raise util.VDVException("Multiple signature OIDs")

                signature_oid = util.decode_oid(data)

            elif tag == util.TAG_MOTICS_SE_SIGNATURE:
                if signature:
                    raise util.VDVException("Multiple signatures")

                signature = data

            elif tag == util.TAG_CERTIFICATE:
                if certificate:
                    raise util.VDVException("Multiple certificates")

                certificate = pki.Certificate.parse_tags(data)

            else:
                raise util.VDVException(f"Unknown tag: 0x{tag:02X}")

        if not identifier:
            raise util.VDVException("No identifier present")
        if not version:
            raise util.VDVException("No version present")
        if not timestamp:
            raise util.VDVException("No timestamp present")
        if not application_data:
            raise util.VDVException("No application data present")
        if not signature_oid:
            raise util.VDVException("No signature OID present")
        if not signature:
            raise util.VDVException("No signature present")

        return cls(
            identifier=identifier,
            version=version,
            random_data=random_data,
            timestamp=timestamp,
            time_offset=time_offset,
            application_data=application_data,
            signature_oid=signature_oid,
            signature=signature,
            certificate=certificate,
            certificate_data=CertificateData.parse(certificate),
            signed_data=signed_data
        )

    @property
    def version_name(self):
        major = self.version // 100000
        minor = (self.version // 1000) % 100
        patch = self.version % 1000

        return f"v{major}.{minor}.{patch}"

    @property
    def random_data_hex(self):
        return ":".join(f"{b:02x}" for b in self.random_data) if self.random_data else None

    @property
    def signature_name(self):
        return oid_to_name(self.signature_oid)

    def verify_signature(self):
        pk = self.certificate_data.public_key.as_cryptography()

        if self.signature_oid == ECDSA_SHA256_OID:
            h = cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                cryptography.hazmat.primitives.hashes.SHA256()
            )
        elif self.signature_oid == ECDSA_SHA384_OID:
            h = cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                cryptography.hazmat.primitives.hashes.SHA384()
            )
        else:
            return False

        try:
            pk.verify(self.signature, self.signed_data, h)
            return True
        except cryptography.exceptions.InvalidSignature:
            return False

@dataclasses.dataclass
class SEId:
    reg_auth_id: int
    ee_type: int
    ee_serial: bytes

    @classmethod
    def parse(cls, data: bytes) -> "SEId":
        if len(data) < 5:
            raise util.VDVException("SE ID too short")

        reg_auth_id = int.from_bytes(data[0:2], "big")
        ee_type = int.from_bytes(data[2:4], "big")

        return cls(reg_auth_id, ee_type, data[4:])

    @property
    def ee_serial_hex(self):
        return ":".join(f"{b:02x}" for b in self.ee_serial)

    def reg_auth_name_opt(self):
        return ticket.map_org_id(self.reg_auth_id, True)

@dataclasses.dataclass
class RootCAReference:
    root_ca_name: str

    @property
    def type(self):
        return "root_ca"

@dataclasses.dataclass
class SubCAReference:
    sub_ca_name: str

    @property
    def type(self):
        return "sub_ca"

@dataclasses.dataclass
class EEReference:
    owner_id: int
    se_id: SEId

    @property
    def type(self):
        return "ee"

    def owner_name_opt(self):
        return ticket.map_org_id(self.owner_id, True)

CHR = typing.Union[RootCAReference, SubCAReference, EEReference]

def parse_chr(data: bytes) -> CHR:
    if data[0] == 1:
        return RootCAReference(data[1:].decode("utf-8"))
    elif data[0] == 2:
        return SubCAReference(data[1:].decode("utf-8"))
    elif data[0] == 3:
        owner_id = int.from_bytes(data[1:3], "big")
        return EEReference(owner_id, SEId.parse(data[3:]))
    else:
        raise util.VDVException(f"Unknown certificate reference type: 0x{data[0]:02X}")


@dataclasses.dataclass
class CertificateData:
    certificate_holder_reference: CHR
    certificate_authority_reference: CHR
    valid_from: datetime.date
    valid_to: datetime.date
    signature_oid: typing.List[int]
    public_key: "pki.ECDSAPublicKey"

    @classmethod
    def parse(cls, data: "pki.Certificate") -> "CertificateData":
        elms = ber_tlv.tlv.Tlv.Parser.parse(data.constructed_content, False, [], False, 0)

        certificate_holder_reference = None
        certificate_authority_reference = None
        valid_from = None
        valid_to = None
        signature_oid = None
        public_key = None

        for tag, data in elms:
            if tag == util.TAG_CERTIFICATE_HOLDER_REFERENCE:
                if certificate_holder_reference:
                    raise util.VDVException("Multiple certificate holder references")

                certificate_holder_reference = parse_chr(data)

            elif tag == util.TAG_CA_REFERENCE:
                if certificate_authority_reference:
                    raise util.VDVException("Multiple certificate authority references")

                certificate_authority_reference = parse_chr(data)

            elif tag == util.TAG_CERTIFICATE_VALID_FROM:
                if valid_from:
                    raise util.VDVException("Multiple valid from")

                n = util.un_bcd(data)
                y = n // 10000
                m = (n // 100) % 100
                d = n % 100
                valid_from = datetime.date(y, m, d)

            elif tag == util.TAG_CERTIFICATE_VALID_UNTIL:
                if valid_to:
                    raise util.VDVException("Multiple valid until")

                n = util.un_bcd(data)
                y = n // 10000
                m = (n // 100) % 100
                d = n % 100
                valid_to = datetime.date(y, m, d)

            elif tag == util.TAG_OID:
                if signature_oid:
                    raise util.VDVException("Multiple signature OIDs")

                signature_oid = util.decode_oid(data)

            elif tag == util.TAG_CERTIFICATE_PUBLIC_KEY:
                if public_key:
                    raise util.VDVException("Multiple certificate public keys")

                public_key = pki.ECDSAPublicKey.from_bytes(data)

            else:
                raise util.VDVException(f"Unknown tag: 0x{tag:02X}")

        if not certificate_holder_reference:
            raise util.VDVException("No certificate holder reference")
        if not certificate_authority_reference:
            raise util.VDVException("No certificate authority reference")
        if not valid_from:
            raise util.VDVException("No valid from")
        if not valid_to:
            raise util.VDVException("No valid until")
        if not signature_oid:
            raise util.VDVException("No signature OID")
        if not public_key:
            raise util.VDVException("No public key")

        return cls(
            certificate_holder_reference=certificate_holder_reference,
            certificate_authority_reference=certificate_authority_reference,
            valid_from=valid_from,
            valid_to=valid_to,
            signature_oid=signature_oid,
            public_key=public_key,
        )

    @property
    def signature_name(self):
        return oid_to_name(self.signature_oid)
