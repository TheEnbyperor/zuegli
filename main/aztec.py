import numpy as np
import cv2
from django.conf import settings


class AztecError(Exception):
    pass


def decode(img_data: bytes, *, scan_speed: str = "slow"):
    try:
        import Barkoder
    except ImportError as e:
        raise AztecError("Barkoder SDK not available") from e

    cfg_response = Barkoder.Config.InitializeWithLicenseKey(settings.BARKODER_LICENSE)
    assert cfg_response.get_result() == Barkoder.ConfigResult.OK
    config = cfg_response.get_config()

    config.encodingCharacterSet = "BINARY"

    match scan_speed.lower():
        case "slow":
            config.decodingSpeed = Barkoder.DecodingSpeed.Slow
        case "normal":
            config.decodingSpeed = Barkoder.DecodingSpeed.Normal
        case "fast":
            config.decodingSpeed = Barkoder.DecodingSpeed.Fast
        case _:
            config.decodingSpeed = Barkoder.DecodingSpeed.Slow

    assert config.set_enabled_decoders([
        Barkoder.DecoderType.Aztec,
        Barkoder.DecoderType.AztecCompact,
        Barkoder.DecoderType.QR,
        Barkoder.DecoderType.QRMicro,
        Barkoder.DecoderType.PDF417,
        Barkoder.DecoderType.PDF417Micro,
    ]).get_result() == Barkoder.ConfigResult.OK

    img = cv2.imdecode(np.asarray(bytearray(img_data), dtype="uint8"), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise AztecError("Unable to read image")

    height, width = img.shape[:2]
    results = Barkoder.Barkoder.DecodeImageMemory(config, img, width, height)

    if len(results) > 0:
        return bytes(results[0].binaryData)
    else:
        raise AztecError("No barcodes found")