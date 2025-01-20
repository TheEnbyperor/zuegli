import bitstring

STRING1 = {
    0: "0",
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "A",
    11: "B",
    12: "C",
    13: "D",
    14: "E",
    15: "F",
    16: "G",
    17: "H",
    18: "I",
    19: "J",
    20: "K",
    21: "L",
    22: "M",
    23: "N",
    24: "O",
    25: "P",
    26: "Q",
    27: "R",
    28: "S",
    29: "T",
    30: "U",
    31: "V",
    32: "W",
    33: "X",
    34: "Y",
    35: "Z",
    36: " ",
    63: "?",
}

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

    def read_string1(self, start: int, end: int) -> str:
        out = ""
        for i in range(start, end, 6):
            out += STRING1[self.data[i:i+6].uint]

        return out

    def read_int(self, start: int, end: int) -> int:
        return self.data[start:end].uint

    def __getitem__(self, index) -> "BitStream":
        if isinstance(index, slice):
            return BitStream(self.data[index])