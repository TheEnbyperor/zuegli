import bitstring
import datetime

class SSBException(Exception):
    pass

class BitStream:
    data: bitstring.ConstBitStream

    def __init__(self, data: bytes):
        self.data = bitstring.ConstBitStream(data)

    def read_bool(self, index: int) -> bool:
        return bool(self.data[index])

    def read_bytes(self, start: int, end: int) -> bytes:
        return self.data[start:end].bytes

    def read_string(self, start: int, end: int) -> str:
        out = bytearray()
        for i in range(start, end, 6):
            out.append(self.data[i:i+6].uint + 0x20)

        return out.decode("ascii").strip()

    def read_int(self, start: int, end: int) -> int:
        return self.data[start:end].uint

    def __getitem__(self, index) -> "BitStream":
        if isinstance(index, slice):
            return BitStream(self.data[index])