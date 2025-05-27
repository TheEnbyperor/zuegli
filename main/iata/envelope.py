import dataclasses
import typing
import base64
import django.core.files.storage
import cryptography.exceptions
import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.primitives.asymmetric.ec
import cryptography.hazmat.primitives.hashes
from . import header, leg, security, util, conditional

@dataclasses.dataclass
class Envelope:
    header: header.Header
    legs: typing.List[leg.Leg]
    conditional: typing.Optional[conditional.UniqueConditional]
    security: typing.Optional[security.Security]
    signed_data: typing.Optional[bytes]

    @property
    def pnr(self):
        return self.legs[0].pnr

    @property
    def sequence(self):
        return self.legs[0].sequence

    @classmethod
    def parse(cls, data: bytes) -> "Envelope":
        try:
            data = data.decode("ascii")
        except UnicodeDecodeError as e:
            raise util.IATAException("Failed to decode IATA data") from e

        if data[0] != "M":
            raise util.IATAException(f"Invalid format code, expected 'M' found '{data[0]}'")

        try:
            number_legs = int(data[1])
        except ValueError as e:
            raise util.IATAException("Failed to decode IATA data") from e

        header_d = header.Header.parse(data[2:23])
        legs = []

        unique_conditional = None

        security_data_parts = data.rsplit("^", 1)
        if len(security_data_parts) == 2:
            data = security_data_parts[0]
            signed_data = data.encode("utf-8")
            security_data = security.Security.parse(security_data_parts[1])
        else:
            security_data = None
            signed_data = None

        data = data[23:]
        for i in range(number_legs):
            l_data = data[:35]
            data = data[35:]

            try:
                variable_size_len = int(data[:2], 16)
                data = data[2:]
            except ValueError as e:
                raise util.IATAException("Invalid variable data length") from e

            variable_data = None
            if variable_size_len:
                variable_data = data[:variable_size_len]
                data = data[variable_size_len:]

                if i == 0 and variable_data[0] == ">":
                    unique_conditional, variable_data = conditional.UniqueConditional.parse(variable_data)

            l = leg.Leg.parse(l_data, unique_conditional=unique_conditional)

            if variable_data:
                l.leg_conditional, l.airline_data = conditional.LegConditional.parse(variable_data)

            legs.append(l)

        return cls(
            header=header_d,
            legs=legs,
            conditional=unique_conditional,
            security=security_data,
            signed_data=signed_data,
        )

    def verify_signature(self) -> typing.Optional[bool]:
        if self.security is None:
            raise util.IATAException("No signed data")

        if not self.conditional:
            return None

        iata_storage = django.core.files.storage.storages["iata-data"]

        try:
            with iata_storage.open(f"keys/{self.conditional.issuer}_{self.security.key_identifier}.pem", "rb") as f:
                pk = cryptography.hazmat.primitives.serialization.load_pem_public_key(f.read())
        except FileNotFoundError:
            return None

        try:
            sig = base64.urlsafe_b64decode(self.security.data)
        except ValueError:
            return False

        try:
            pk.verify(sig, self.signed_data, cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                cryptography.hazmat.primitives.hashes.SHA256(),
            ))
        except cryptography.exceptions.InvalidSignature:
            return False

        return True
