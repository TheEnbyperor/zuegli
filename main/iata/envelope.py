import dataclasses
import typing
from . import header, leg, security, util, conditional

@dataclasses.dataclass
class Envelope:
    header: header.Header
    legs: typing.List[leg.Leg]
    conditional: typing.Optional[conditional.UniqueConditional]
    security: typing.Optional[security.Security]

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

        data = data[23:]
        security_data_parts = data.rsplit("^", 1)
        if len(security_data_parts) == 2:
            data = security_data_parts[0]
            security_data = security.Security.parse(security_data_parts[1])
        else:
            security_data = None

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
        )
