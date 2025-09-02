import numpy as np
import cv2
from django.conf import settings

try:
    import Barkoder
    barkoder_cfg_response = Barkoder.Config.InitializeWithLicenseKey(settings.BARKODER_LICENSE)
    assert barkoder_cfg_response.get_result() == Barkoder.ConfigResult.OK
    barkoder_config = barkoder_cfg_response.get_config()
    barkoder_config.encodingCharacterSet = "BINARY"
    assert barkoder_config.set_enabled_decoders([
        Barkoder.DecoderType.Aztec,
        Barkoder.DecoderType.AztecCompact,
        Barkoder.DecoderType.QR,
        Barkoder.DecoderType.QRMicro,
        Barkoder.DecoderType.PDF417,
        Barkoder.DecoderType.PDF417Micro,
    ]).get_result() == Barkoder.ConfigResult.OK
except ImportError as e:
    barkoder_config = None

class AztecError(Exception):
    pass

def decode_multiple(img_data: bytes, *, scan_speed: str = "slow"):
    if not barkoder_config:
        raise AztecError("Barkoder SDK not available")

    match scan_speed.lower():
        case "slow":
            barkoder_config.decodingSpeed = Barkoder.DecodingSpeed.Slow
        case "normal":
            barkoder_config.decodingSpeed = Barkoder.DecodingSpeed.Normal
        case "fast":
            barkoder_config.decodingSpeed = Barkoder.DecodingSpeed.Fast
        case _:
            barkoder_config.decodingSpeed = Barkoder.DecodingSpeed.Slow

    img = cv2.imdecode(np.asarray(bytearray(img_data), dtype="uint8"), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise AztecError("Unable to read image")

    height, width = img.shape[:2]
    results = Barkoder.Barkoder.DecodeImageMemory(barkoder_config, img, width, height)

    if len(results) > 0:
        d = [bytes(r.binaryData) for r in results]
        del results
        return d
    else:
        del results
        raise AztecError("No barcodes found")

def decode(img_data: bytes, *, scan_speed: str = "slow"):
    return decode_multiple(img_data, scan_speed=scan_speed)[0]