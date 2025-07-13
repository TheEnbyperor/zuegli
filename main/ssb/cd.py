import dataclasses
import re
import decimal
import typing
import pathlib
import json
from ..uic import cd

@dataclasses.dataclass
class CDData:
    price: typing.Optional[decimal.Decimal]
    distance: typing.Optional[decimal.Decimal]
    other_blocks: typing.Dict[str, str]

    @classmethod
    def parse(cls, data: str):
        blocks = data.split(",")

        price = None
        distance = None
        other_blocks = {}

        for block in blocks:
            block_id = block[0]
            block_data = block[1:]

            if block_id == "C":
                try:
                    price = decimal.Decimal(block_data) / decimal.Decimal("100")
                except ValueError as e:
                    raise cd.CDException("Invalid price") from e
            elif block_id == "D":
                try:
                    distance = decimal.Decimal(block_data)
                except ValueError as e:
                    raise cd.CDException("Invalid distance") from e
            else:
                other_blocks[block_id] = block_data

        return cls(
            price=price,
            distance=distance,
            other_blocks=other_blocks
        )

    def price_str(self):
        return f"Kč {self.price:.2f}"