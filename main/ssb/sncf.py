import dataclasses
import decimal


@dataclasses.dataclass
class SNCFData:
    price: decimal.Decimal

    def price_str(self):
        return f"{self.price:.2f} €"