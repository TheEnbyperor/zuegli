import dataclasses
import typing

BORDGASTRONOMIE_30         = "N10001311299"
BORDGASTRONOMIE_GUTSHEIN_5 = "N00014311299"
LOUNGE_PREMIUM             = "LOUUP0010000"
LOUNGE_STANDARD            = "LOUUS0010000"
BAHNBONUS                  = "BB0001661749"

@dataclasses.dataclass
class Product:
    name: str
    strip_image: typing.Optional[str] = None
    strip_colour: typing.Optional[str] = None

PRODUCTS = {
    BORDGASTRONOMIE_30: Product(
        name="30% Rabatt Bordgastronomie",
        strip_image="bahnbonus/bg-platinum.png",
        strip_colour="#000000",
    ),
    BORDGASTRONOMIE_GUTSHEIN_5: Product(
        name="Gutschein 5€ in der Bordgastronomie",
        strip_image="bahnbonus/bg-normal.png",
        strip_colour="#ffffff",
    ),
    BAHNBONUS: Product(
        name="BahnBonus in der Bordgastronomie",
        strip_image="bahnbonus/bg-normal.png",
        strip_colour="#ffffff",
    ),
    LOUNGE_PREMIUM: Product(
        name="Premium Lounge",
        strip_image="bahnbonus/bg-platinum.png",
        strip_colour="#000000",
    ),
    LOUNGE_STANDARD: Product(
        name="Lounge",
        strip_image="bahnbonus/bg-gold.png",
        strip_colour="#000000",
    ),
}
