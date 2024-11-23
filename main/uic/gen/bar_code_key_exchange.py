from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from xsdata.models.datatype import XmlDate


@dataclass
class BarcodeStructureType:
    issuer_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "issuerName",
            "type": "Element",
            "required": True,
        },
    )
    issuer_code: Optional[int] = field(
        default=None,
        metadata={
            "name": "issuerCode",
            "type": "Element",
            "required": True,
        },
    )
    version_type: Optional[str] = field(
        default=None,
        metadata={
            "name": "versionType",
            "type": "Element",
            "required": True,
        },
    )
    id: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "required": True,
        },
    )
    barcode_version: Optional[int] = field(
        default=None,
        metadata={
            "name": "barcodeVersion",
            "type": "Element",
            "required": True,
        },
    )
    description: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )


class KeyTypeKeyForged(Enum):
    TRUE = "true"
    FALSE = "false"
    VALUE_1 = "1"
    VALUE_0 = "0"
    VALUE = ""


@dataclass
class PublicKeyType:
    class Meta:
        name = "publicKeyType"

    value: Optional[bytes] = field(
        default=None,
        metadata={
            "required": True,
            "format": "base64",
        },
    )
    keytype: str = field(
        default="CERTIFICATE",
        metadata={
            "type": "Attribute",
        },
    )


class TestbarcodeImagetype(Enum):
    JPG = "jpg"
    PNG = "png"
    BMP = "bmp"


@dataclass
class KeyType:
    issuer_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "issuerName",
            "type": "Element",
            "required": True,
        },
    )
    issuer_code: Optional[int] = field(
        default=None,
        metadata={
            "name": "issuerCode",
            "type": "Element",
            "required": True,
        },
    )
    version_type: Optional[str] = field(
        default=None,
        metadata={
            "name": "versionType",
            "type": "Element",
            "required": True,
        },
    )
    signature_algorithm: Optional[str] = field(
        default=None,
        metadata={
            "name": "signatureAlgorithm",
            "type": "Element",
            "required": True,
        },
    )
    signature_algorithm_oid: Optional[str] = field(
        default=None,
        metadata={
            "name": "signatureAlgorithmOid",
            "type": "Element",
        },
    )
    id: Optional[int] = field(
        default=None,
        metadata={
            "type": "Element",
            "required": True,
        },
    )
    public_key: Optional[PublicKeyType] = field(
        default=None,
        metadata={
            "name": "publicKey",
            "type": "Element",
            "required": True,
        },
    )
    barcode_version: Optional[int] = field(
        default=None,
        metadata={
            "name": "barcodeVersion",
            "type": "Element",
            "required": True,
        },
    )
    start_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "startDate",
            "type": "Element",
            "required": True,
        },
    )
    end_date: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "endDate",
            "type": "Element",
            "required": True,
        },
    )
    barcode_xsd: Optional[str] = field(
        default=None,
        metadata={
            "name": "barcodeXsd",
            "type": "Element",
        },
    )
    allowed_product_owner_codes: Optional[
        "KeyType.AllowedProductOwnerCodes"
    ] = field(
        default=None,
        metadata={
            "name": "allowedProductOwnerCodes",
            "type": "Element",
            "required": True,
        },
    )
    last_day_of_sale: Optional[XmlDate] = field(
        default=None,
        metadata={
            "name": "lastDayOfSale",
            "type": "Element",
        },
    )
    key_forged: Optional[KeyTypeKeyForged] = field(
        default=None,
        metadata={
            "name": "keyForged",
            "type": "Element",
        },
    )
    comment_for_encryption_type: Optional[str] = field(
        default=None,
        metadata={
            "name": "commentForEncryptionType",
            "type": "Element",
            "required": True,
        },
    )
    testbarcode: Optional["KeyType.Testbarcode"] = field(
        default=None,
        metadata={
            "type": "Element",
        },
    )

    @dataclass
    class AllowedProductOwnerCodes:
        product_owner_code: List[int] = field(
            default_factory=list,
            metadata={
                "name": "productOwnerCode",
                "type": "Element",
            },
        )
        product_owner_name: List[str] = field(
            default_factory=list,
            metadata={
                "name": "productOwnerName",
                "type": "Element",
            },
        )

    @dataclass
    class Testbarcode:
        imagetype: Optional[TestbarcodeImagetype] = field(
            default=None,
            metadata={
                "type": "Element",
                "required": True,
            },
        )
        imagedata: Optional[bytes] = field(
            default=None,
            metadata={
                "type": "Element",
                "required": True,
                "format": "base64",
            },
        )


@dataclass
class Keys:
    class Meta:
        name = "keys"

    key: List[KeyType] = field(
        default_factory=list,
        metadata={
            "type": "Element",
        },
    )
    barcode_structure: List[BarcodeStructureType] = field(
        default_factory=list,
        metadata={
            "name": "barcodeStructure",
            "type": "Element",
        },
    )
