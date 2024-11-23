from dataclasses import dataclass, field
from typing import List, Optional

__NAMESPACE__ = "http://ws.refdata.crd.cc.uic.org/replication/schemas"


@dataclass
class Country:
    class Meta:
        namespace = "http://ws.refdata.crd.cc.uic.org/replication/schemas"

    country_iso_code: Optional[str] = field(
        default=None,
        metadata={
            "name": "Country_ISO_Code",
            "type": "Element",
            "required": True,
        },
    )
    country_uic_code: Optional[int] = field(
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
        },
    )
    country_name_fr: Optional[str] = field(
        default=None,
        metadata={
            "name": "Country_Name_FR",
            "type": "Element",
            "required": True,
        },
    )
    country_name_de: Optional[str] = field(
        default=None,
        metadata={
            "name": "Country_Name_DE",
            "type": "Element",
            "required": True,
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
