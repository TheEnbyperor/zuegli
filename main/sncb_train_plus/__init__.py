import json
import dataclasses
from .util import SNCBTrainPlusException

def is_sncb_train_plus_code(code: bytes) -> bool:
    try:
        v = json.loads(code)
        return isinstance(v, dict) and "advantageCardNumber" in v
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


@dataclasses.dataclass
class TrainPlusCode:
    card_number: str

    @classmethod
    def parse(cls, code: bytes) -> "TrainPlusCode":
        try:
            d = json.loads(code)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise SNCBTrainPlusException("Invalid train plus barcode") from e

        if "advantageCardNumber" not in d:
            raise SNCBTrainPlusException("Invalid train plus barcode")

        return cls(
            card_number=d["advantageCardNumber"],
        )
