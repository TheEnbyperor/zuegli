import dataclasses
import typing
import datetime
from ..vdv import ticket, org_id, product_id

class DBVUException(Exception):
    pass

@dataclasses.dataclass
class DBRecordVU:
  traveller_count: int
  products: typing.List["DBVUProduct"]

  @classmethod
  def parse(cls, data: bytes, version: int, context: "ticket.Context"):
    if version != 1:
      raise DBVUException(f"Unsupported record version {version}")

    offset = 5
    traveller_count = int.from_bytes(data[offset:offset+1])

    offset += 1
    __num_products = int.from_bytes(data[offset:offset+1])

    offset += 1
    products = []

    # Iterates over the announced number of products
    # However, the DBVUProduct does not necessarily have a statically defined length...
    # So we do something ugly where we ask it to self-report it's length after it's been instantiated.
    # If it works, etc.
    for _ in range(__num_products):
      product = DBVUProduct(data[offset:], context)
      products += [product]
      offset += product.get_length()

    return cls(
        traveller_count=traveller_count,
        products=products
    )

@dataclasses.dataclass
class DBVUProduct:
  product_authorization: "DBVUProductAuthorization" # Struktur "Berechtigung_ID"
  product_details: "DBVUProductDetails"             # Struktur "EFMProdukt_ID"

  validity_start: datetime.datetime                 # GueltigAb
  validity_end: datetime.datetime                   # GueltigBis
  cost: typing.Optional[str]                        # Preis
  sequence_number: typing.Optional[int]             # Sequenznummer (SAM)
  product_data: typing.List["ticket.ELEMENT"]

  def __init__(self, data: bytes, context: "ticket.Context"):
    self.__data = data
    offset = 0
    self.product_authorization = DBVUProductAuthorization(data[offset:offset+6])

    offset += 6
    self.product_details = DBVUProductDetails(data[offset:offset+4])

    offset += 4
    self.validity_start = DateTimeCompactParser(data[offset:offset+4]).get_datetime()

    offset += 4
    self.validity_end = DateTimeCompactParser(data[offset:offset+4]).get_datetime()

    offset += 4

    # "Separate Daten - Statischer produktspezifischer Teil"
    # This rare case happens if the "Preis" field has as value 0x85ZZZZ
    if data[offset] == 0x85:
      self.cost = None
      self.sequence_number = None

      # Length of full block is announced
      offset += 1
      multi_tag_total_length = data[offset]

      offset += 1
      end_length = offset + multi_tag_total_length - 2

      self.product_data = []

      while offset < end_length - 1:
        struct_type = data[offset]                          # Sub-block type is announced
        struct_length = data[offset+1]                      # Sub-block length is announced
        struct_data = data[offset+2:offset+2+struct_length] # Sub-block data is remaining bytes.
        self.product_data.append(ticket.VDVTicket.parse_product_data_element((struct_type, struct_data), context))
        offset += struct_length+2

    # If the 0080VU spec is "as standard"
    else:
      # Formatting here for convenience.
      self.cost = f"{int.from_bytes(data[offset:offset+3]) / 100:.2f}"

      offset += 3
      self.sequence_number = int.from_bytes(data[offset:offset+4])

      offset += 4
      data_fields_length = int.from_bytes(data[offset:offset+1])

      # Will automatically convert to a DBVUTAGListe type.
      offset += 1
      self.product_data = [ticket.SpacialValidity.parse(data[offset+2:offset+data_fields_length])]

      offset += data_fields_length

    # Ensure that the content size matches for self-reporting of data length.
    self.__data = data[0:offset]

  def get_length(self) -> int:
    return len(self.__data)

@dataclasses.dataclass
class DBVUProductAuthorization:
  authorization_number: int # BerechtigungNr
  issuer_id: int            # KVPOrgID

  def __init__(self, data: bytes):
    self.__data = data

    self.authorization_number = int.from_bytes(data[0:4])
    self.issuer_id = int.from_bytes(data[4:6])

  @property
  def issuer(self):
    org, is_test = org_id.get_org(self.issuer_id)
    if org:
      if is_test:
        return f"{org['name']} (Test)"
      else:
        return org['name']


@dataclasses.dataclass
class DBVUProductDetails:
  product_type_id: int  # ProduktNr
  issuer_id: int        # PVOrgID

  def __init__(self, data: bytes):
    self.__data = data

    self.product_type_id = int.from_bytes(data[0:2])
    self.issuer_id = int.from_bytes(data[2:4])

  @property
  def issuer(self):
    org, is_test = org_id.get_org(self.issuer_id)
    if org:
      if is_test:
        return f"{org['name']} (Test)"
      else:
        return org['name']

  @property
  def product_type(self):
    product_id_map = product_id.get_product_id_list()
    if name := product_id_map.get((self.issuer_id, self.product_type_id)):
      return name


class DateTimeCompactParser:
  date: datetime.datetime

  # Decode method pulled from
  # https://web.archive.org/web/20200920202413/https://www.kcd-nrw.de/fileadmin/03_KC_Seiten/KCD/Downloads/Technische_Dokumente/Archiv/2010_02_12_kompendiumvrrfa2dvdv_1_4.pdf
  def __init__(self, data: bytes):
    self.__data = data
    data = int.from_bytes(data)

    second = data & 0x1F
    minute = (data >> 5) & 0x3F
    hour = ((data >> 11) & 0x1F)
    day = (data >> 16) & 0x1F
    month = (data >> 21) & 0xF
    year = 1990 + ((data >> 25) & 0x7F)

    self.date = datetime.datetime(year, month, day, 0, minute, second) + datetime.timedelta(0, 3600*hour)

  def get_datetime(self) -> datetime.datetime:
    return self.date
