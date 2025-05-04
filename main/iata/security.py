import dataclasses
from . import util

@dataclasses.dataclass
class Security:
    key_identifier: str
    data: str

    @classmethod
    def parse(cls, data: str) -> "Security":
        kid = data[0]
        try:
            s_len = int(data[1:3], 16)
        except ValueError as e:
            raise util.IATAException("Invalid security record length") from e

        if len(data) + 3 < s_len:
            raise util.IATAException("Not enough data")

        return cls(
            key_identifier=kid,
            data=data[3:3 + s_len],
        )
