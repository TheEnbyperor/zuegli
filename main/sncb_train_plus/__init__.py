import json
import dataclasses
from .util import SNCBTrainPlusException

def is_sncb_train_plus_code(code: bytes) -> bool:
    try:
        return "advantageCardNumber" in json.loads(code)
    except json.JSONDecodeError:
        return False


@dataclasses.dataclass
class TrainPlusCode:
    card_number: str

    @classmethod
    def parse(cls, code: bytes) -> "TrainPlusCode":
        try:
            d = json.loads(code)
        except json.JSONDecodeError as e:
            raise SNCBTrainPlusException("Invalid train plus barcode") from e

        if "advantageCardNumber" not in d:
            raise SNCBTrainPlusException("Invalid train plus barcode")

        return cls(
            card_number=d["advantageCardNumber"],
        )
