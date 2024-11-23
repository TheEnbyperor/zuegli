from dataclasses import dataclass, field
from typing import List, Optional

__NAMESPACE__ = "http://ws.refdata.crd.cc.uic.org/replication/schemas"


@dataclass
class CountryIsoCode1:
    """
    Identifies a County or State by code (ISO 3166-1)
    """

    class Meta:
        name = "Country_ISO_Code"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "min_length": 2,
            "max_length": 2,
            "white_space": "collapse",
        },
    )


@dataclass
class CountryUicCode:
    """
    Standard numerical country coding for use in railway traffic (UIC Leaflet
    920-14)
    """

    class Meta:
        name = "Country_UIC_Code"
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    value: str = field(
        default="",
        metadata={
            "min_inclusive": "10",
            "max_inclusive": "99",
        },
    )


@dataclass
class Country:
    """
    :ivar country_iso_code:
    :ivar country_uic_code:
    :ivar country_name_en: English name of the country
    :ivar country_name_fr: French name of the country
    :ivar country_name_de: name of the country in German language
    :ivar sub_loc_code_flag: allow subsidiary location change
    """

    class Meta:
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    country_iso_code: Optional[CountryIsoCode1] = field(
        default=None,
        metadata={
            "name": "Country_ISO_Code",
            "type": "Element",
            "required": True,
        },
    )
    country_uic_code: Optional[CountryUicCode] = field(
        default=None,
        metadata={
            "name": "Country_UIC_Code",
            "type": "Element",
        },
    )
    country_name_en: Optional[str] = field(
        default=None,
        metadata={
            "name": "Country_Name_EN",
            "type": "Element",
            "required": True,
            "max_length": 255,
        },
    )
    country_name_fr: Optional[str] = field(
        default=None,
        metadata={
            "name": "Country_Name_FR",
            "type": "Element",
            "max_length": 255,
        },
    )
    country_name_de: Optional[str] = field(
        default=None,
        metadata={
            "name": "Country_Name_DE",
            "type": "Element",
            "max_length": 255,
        },
    )
    sub_loc_code_flag: Optional[str] = field(
        default=None,
        metadata={
            "name": "Sub_Loc_Code_Flag",
            "type": "Element",
        },
    )


@dataclass
class Countries:
    class Meta:
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    country: List[Country] = field(
        default_factory=list,
        metadata={
            "name": "Country",
            "type": "Element",
            "min_occurs": 1,
        },
    )
