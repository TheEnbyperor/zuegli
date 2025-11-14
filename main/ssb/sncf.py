import dataclasses
import decimal
import typing


def parse_bitmap(validity_zones: bytes) -> typing.Set[int]:
    validity_zones_int = int.from_bytes(validity_zones, "big")
    out = set()
    for b in range(len(validity_zones) * 8):
        if validity_zones_int & (1 << b):
            out.add(b + 1)
    return out


@dataclasses.dataclass
class SNCFData:
    network_id: int
    contract_provider: int
    tariff_code: str
    via: typing.Optional[int]
    validity_zones: set
    price: decimal.Decimal
    payment_method: int
    retail_channel: str
    distance_km: int
    terminal_id: str
    route_constraint: bool

    def contract_provider_str(self):
        if self.contract_provider == 2:
            return "SNCF"
        else:
            return None

    def retail_channel_str(self):
        if self.retail_channel == "01":
            return "Distributeur de Billets Régionaux"
        elif self.retail_channel == "02":
            return "buraliste Novater"
        elif self.retail_channel == "03":
            return "BLS+"
        elif self.retail_channel == "04":
            return "PVM"
        elif self.retail_channel == "05":
            return "TAPAS"
        elif self.retail_channel == "00":
            return "Other"
        else:
            return f"Unknown - {self.retail_channel}"

    def price_str(self):
        return f"{self.price:.2f} €"