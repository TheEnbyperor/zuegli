import dataclasses
import typing
import datetime
from . import codes, stations

class DBVUException(Exception):
    pass

@dataclasses.dataclass
class DBRecordVU:
  traveller_count: int
  products: typing.List["DBVUProduct"]

  @classmethod
  def parse(cls, data: bytes, version: int):
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
      product = DBVUProduct(data[offset:])
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
  tag_fields: typing.List["DBVUTAGFields"]          # Flächenlistenelemente

  def __init__(self, data: bytes):
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

      self.tag_fields = []

      while offset < end_length - 1:
        struct_type = data[offset]                          # Sub-block type is announced
        struct_length = data[offset+1]                      # Sub-block length is announced
        struct_data = data[offset+2:offset+2+struct_length] # Sub-block data is remaining bytes.
        self.tag_fields += [DBVUTAGFields(struct_type, struct_length, struct_data)]
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
      self.tag_fields = [DBVUTAGFields(0xDC, data_fields_length, data[offset+2:offset+data_fields_length])]

      offset += data_fields_length

    # Ensure that the content size matches for self-reporting of data length.
    self.__data = data[0:offset]

  def get_length(self) -> int:
    return len(self.__data)

@dataclasses.dataclass
class DBVUProductAuthorization:
  authorization_number: int # BerechtigungNr
  issuer_id: int            # KVPOrgID
  issuer: str

  def __init__(self, data: bytes):
    self.__data = data

    self.authorization_number = int.from_bytes(data[0:4])

    self.issuer_id = int.from_bytes(data[4:6])
    self.issuer = codes.ORGANIZATION_IDS[self.issuer_id] if self.issuer_id in codes.ORGANIZATION_IDS.keys() else "Unknown"

@dataclasses.dataclass
class DBVUProductDetails:
  product_type_id: int  # ProduktNr
  product_type: str

  issuer_id: int        # PVOrgID
  issuer: str

  def __init__(self, data: bytes):
    self.__data = data

    self.product_type_id = int.from_bytes(data[0:2])
    self.product_type = codes.PRODUCTS[self.product_type_id] if self.product_type_id in codes.PRODUCTS.keys() else "Unknown"

    self.issuer_id = int.from_bytes(data[2:4])
    self.issuer = codes.ORGANIZATION_IDS[self.issuer_id] if self.issuer_id in codes.ORGANIZATION_IDS.keys() else "Unknown"

@dataclasses.dataclass
class DBVUTAGFields:
  field_type: int
  field_length: int

  # Python hack to invert the instantiation flow and instantiate the correct type of sub-object based on the inferred field_type
  # Inspired by https://stackoverflow.com/questions/47984126/initializing-a-subclass-on-condition-from-the-parent-class-initialisation
  def __new__(cls, field_type: int, field_length: int, data: bytes):
    match field_type:
      case 0xDA: # TAG "Grundlegende Daten_neu"
        instance = super(DBVUTAGFields, cls).__new__(DBVUTAGGrundlegendeDatenNeu)
      case 0xDB: # TAG "Fahrgast"
        instance = super(DBVUTAGFields, cls).__new__(DBVUTAGFahrgast)
      case 0xE0: # TAG "Identifikationsmedium"
        instance = super(DBVUTAGFields, cls).__new__(DBVUTAGIdentifikationsmedium)
      case 0xDC: # TAG "Liste"
        instance = super(DBVUTAGFields, cls).__new__(DBVUTAGListe)
      case _: # Unknown
        instance = super(DBVUTAGFields, cls).__new__(DBVUTAGUnbekannt)

    instance.__data = data
    return instance

@dataclasses.dataclass
class DBVUTAGGrundlegendeDatenNeu(DBVUTAGFields):
  payment_type: int                         # berBezahlArt.code
  passenger_fare_category: int              # efsFahrgastTyp .code
  travelers_standard: "DBVUTAGEFSMitnahme"  # efs_mitnahme_1
  travelers_other: "DBVUTAGEFSMitnahme"     # efs_mitnahme_2
  transport_category: int                   # efs_verkehrsmittel_kategorie_code
  service_class: int                        # efs_service_klasse_code
  price_brut: str                           # efs_preis
  price_vat: int                            # efs_mehrwertsteuer
  price_level: int                          # efs_preisstufe
  internal_product_number: int              # efs_verkaufs_produkt_nummer

  def __init__(self, field_type: int, field_length: int, data: bytes):
    self.field_type = field_type
    self.field_length = field_length

    self.payment_type = data[0]
    self.passenger_fare_category = data[1]
    self.travelers_standard = DBVUTAGEFSMitnahme(data[2], data[3])
    self.travelers_other = DBVUTAGEFSMitnahme(data[4], data[5])
    self.transport_category = data[6]
    self.service_class = data[7]
    self.price_brut = f"{int.from_bytes(data[8:8+3]) / 100:.2f}"
    self.price_vat = f"{int.from_bytes(data[11:11+2]) / 100:.2f}"
    self.price_level = data[13]
    self.internal_product_number = int.from_bytes(data[14:14+3])


@dataclasses.dataclass
class DBVUTAGFahrgast(DBVUTAGFields):
  passenger_gender: int             # efs_fahrgast_geschlecht
  passenger_dob:    datetime.date   # efs_fahrgast_geburtsdatum
  passenger_name:   str             # efs_fahrgast_name

  def __init__(self, field_type: int, field_length: int, data: bytes):
    self.field_type = field_type
    self.field_length = field_length

    self.passenger_gender = data[0]

    if data[1:5] != b'00000000':
      # TODO: Check whether data well formed as no formal example in docs.
      self.passenger_dob = datetime.date(
        year=int(f"{data[3]:02x}{data[4]:02x}"),  # Because encoded as \xYY\xYY
        month=int(f"{data[2]:02x}"),              # Because encoded as \xmm
        day=int(f"{data[1]:02x}")                 # Because encoded as \xDD
      )
    else:
      self.passenger_dob = None

    self.passenger_name = data[5:].decode('utf-8')

@dataclasses.dataclass
class DBVUTAGIdentifikationsmedium(DBVUTAGFields):
  id_type: int    # efs_identifikationsmedium_typ
  id_number: str  # efs_identifikations_medium_nummer

  def __init__(self, field_type: int, field_length: int, data: bytes):
    self.field_type = field_type
    self.field_length = field_length

    self.id_type = data[0]
    self.id_number = data[1:].decode('utf-8')

@dataclasses.dataclass
class DBVUTAGListe(DBVUTAGFields):
  organization_id: int
  organization: str

  field_type_definition: str
  field_typecode: int
  field_data_id: str
  field_data: typing.Dict[str, typing.Any]

  def __init__(self, field_type: int, field_length: int, data: bytes):
    self.field_type = field_type
    self.field_length = field_length

    self.organization_id = int.from_bytes(data[1:3])
    self.organization = codes.ORGANIZATION_IDS[self.organization_id] if self.organization_id in codes.ORGANIZATION_IDS.keys() else "Unknown"

    self.field_typecode = data[0]
    self.field_type_definition = codes.PRODUCT_TYPE_DEFINITION[self.field_typecode] if self.field_typecode in codes.PRODUCT_TYPE_DEFINITION.keys() else "Unknown"

    self.field_data_id = int.from_bytes(data[3:])

    # If expected standard UIC location code
    if self.organization_id != 5000:
      self.field_data = stations.get_station_by_db(self.field_data_id)
    # If location is in fact a region.
    elif self.organization_id == 5000 and self.field_data_id in codes.VDV_KAKG_PLACES.keys():
      self.field_data = { 'name': codes.VDV_KAKG_PLACES[self.field_data_id] }
    else:
      # Alternatively, set to "Bielefeld", as it is well known that Bielefeld does not exist.
      self.field_data = { 'name': 'Unknown' }

@dataclasses.dataclass
class DBVUTAGUnbekannt(DBVUTAGFields):
  def __init__(self, field_type: int, field_length: int, data: bytes):
    self.field_type = field_type
    self.field_length = field_length

@dataclasses.dataclass
class DBVUTAGEFSMitnahme:
  passenger_type: int  # mitnahmeTyp
  passenger_count: int # mitnahmeAnzahl

  def __init__(self, type: int, count: int):
    self.passenger_type = type
    self.passenger_count = count

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
