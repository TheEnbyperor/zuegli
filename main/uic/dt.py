import dataclasses
import typing
import datetime
import pytz

TZ = pytz.timezone("Europe/Berlin")

class DTException(Exception):
    pass

def parse_tlv(data: bytes):
    offset = 0
    blocks = {}
    while offset < len(data):
        try:
            block_id = data[offset:offset+3].decode("utf-8")
        except UnicodeDecodeError as e:
            raise DTException(f"Invalid TLV record") from e
        try:
            block_len = int(data[offset+3:offset+7].decode("utf-8"), 10)
        except (ValueError, UnicodeDecodeError) as e:
            raise DTException(f"Invalid TLV record") from e
        try:
            block_data = data[offset+7:offset+7+block_len].decode("utf-8")
        except UnicodeDecodeError as e:
            raise DTException(f"Invalid TLV record") from e
        offset += block_len + 7

        if block_data == "null":
            continue

        blocks[block_id] = block_data

    return blocks

@dataclasses.dataclass
class DTRecordTI:
    product_name: typing.Optional[str]
    validity_start: typing.Optional[datetime.datetime]
    validity_end: typing.Optional[datetime.datetime]
    start_stop: typing.Optional[str]
    start_zone: typing.Optional[str]
    end_zone: typing.Optional[str]
    other_blocks: typing.Dict[str, str]

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise DTException(f"Unsupported record version {version}")

        blocks = parse_tlv(data)
        product_name = None
        validity_start = None
        validity_end = None
        start_stop = None
        start_zone = None
        end_zone = None

        if block_data := blocks.pop("001", None):
            product_name = block_data
        if block_data := blocks.pop("002", None):
            try:
                validity_start = TZ.localize(datetime.datetime.strptime(block_data, "%Y-%m-%d %H:%M"))
            except ValueError:
                try:
                    validity_start = datetime.datetime.fromisoformat(block_data)
                except ValueError as e:
                    raise DTException(f"Invalid validity start date") from e
        if block_data := blocks.pop("003", None):
            try:
                validity_end = TZ.localize(datetime.datetime.strptime(block_data, "%Y-%m-%d %H:%M"))
            except ValueError:
                try:
                    validity_end = datetime.datetime.fromisoformat(block_data)
                except ValueError as e:
                    raise DTException(f"Invalid validity end date") from e
        if block_data := blocks.pop("004", None):
            start_stop = block_data
        if block_data := blocks.pop("005", None):
            start_zone = block_data
        if end_zone := blocks.pop("006", None):
            end_zone = block_data

        return cls(
            product_name=product_name,
            validity_start=validity_start,
            validity_end=validity_end,
            start_stop=start_stop,
            start_zone=start_zone,
            end_zone=end_zone,
            other_blocks=blocks,
        )


@dataclasses.dataclass
class DTRecordPA:
    passenger_name: typing.Optional[str]
    customer_id: typing.Optional[str]
    other_blocks: typing.Dict[str, str]

    @classmethod
    def parse(cls, data: bytes, version: int):
        if version != 1:
            raise DTException(f"Unsupported record version {version}")

        blocks = parse_tlv(data)
        passenger_name = None
        customer_id = None

        if block_data := blocks.pop("001", None):
            passenger_name = block_data
        if block_data := blocks.pop("002", None):
            customer_id = block_data

        return cls(
            passenger_name=passenger_name,
            customer_id=customer_id,
            other_blocks=blocks,
        )