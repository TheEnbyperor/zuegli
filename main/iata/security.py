import dataclasses
from . import util

@dataclasses.dataclass
class Security:
    type: str
    data: str

    @classmethod
    def parse(cls, data: str) -> "Security":
        s_type = data[0]
        try:
            s_len = int(data[1:3], 16)
        except ValueError as e:
            raise util.IATAException("Invalid security record length") from e

        if len(data) + 3 < s_len:
            raise util.IATAException("Not enough data")

        return cls(
            type=s_type,
            data=data[3:3 + s_len],
        )
