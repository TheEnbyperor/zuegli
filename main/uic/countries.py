import pathlib
import typing
import xsdata.formats.dataclass.parsers
from . import gen


COUNTRIES = None
ROOT_DIR = pathlib.Path(__file__).parent

xml_parser = xsdata.formats.dataclass.parsers.XmlParser()


def get_country_list() -> typing.Dict[str, gen.country_code.Country]:
    global COUNTRIES

    if COUNTRIES:
        return COUNTRIES

    data = xml_parser.from_path(
        ROOT_DIR / "data" / "country_codes_2024_03_13.xml",
        gen.country_code.Countries,
    )
    COUNTRIES = {}
    for country in data.country:
        if country.country_uic_code:
            COUNTRIES[country.country_uic_code.value] = country

    return COUNTRIES


def get_country_name_by_uic(code) -> typing.Optional[dict]:
    if i := get_country_list().get(str(code)):
        return i.country_name_en