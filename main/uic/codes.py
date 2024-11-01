import typing

ORGANIZATION_IDS: typing.Dict[int, str] = {
  6260: "DB Vertrieb GmbH",
  6262: "DB Fernverkehr",
  6263: "DB Regio Zentrale",
  5000: "VDV-KA KG",
  0xAAAA: "KCM"
}

PRODUCTS: typing.Dict[int, str] = {
  2000:	"City-Ticket",
  1000:	"City-mobil Einzelfahrt",
  1001:	"City-mobil Tageskarte",
  1002:	"Baden-Württemberg-Ticket",
  1004:	"Baden-Württemberg-Ticket Nacht",
  1005:	"Bayern-Ticket",
  1007:	"Bayern-Ticket-Nacht",
  1008:	"Brandenburg-Berlin-Ticket",
  1009:	"Brandenburg-Berlin-Ticket-Nacht",
  1010:	"Mecklenburg-Vorpommern-Ticket",
  1011:	"Niedersachsen-Ticket",
  1012:	"Rheinland-Pfalz-Ticket",
  1013:	"Rheinland-Pfalz-Ticket-Nacht",
  1014:	"Saarland-Ticket",
  1015:	"Saarland-Ticket-Nacht",
  1016:	"Sachsen-Anhalt-Ticket",
  1017:	"Sachsen-Ticket",
  1018:	"Schleswig-Holstein-Ticket",
  1019:	"Thüringen-Ticket",
  1020:	"Rheinland-Pfalz-Ticket + Luxemburg",
  1022:	"Bayern-Böhmen-Ticket",
  1030:	"Sachsen-Anhalt-Ticket plus Westharz",
  1031:	"Thüringen-Ticket  plus Westharz",
  1032:	"Sachsen-Ticket plus Westharz",
  1200:	"Schönes-Wochenende-Ticket",
  1201:	"Quer-Durchs-Land-Ticket",
  1202:	"9-Euro-Ticket",
  9999:	"Deutschlandticket",
  3000:	"In-Out-System"
}

PRODUCT_TYPE_DEFINITION: typing.Dict[int, str] = {
  0x05: "SchönerTagTicket NRW",
  0x0d: "City-Ticket / City-mobil",
  0x10: "Länderticket / Schönes-Wochenende-Ticket / Quer-Durchs-Land-Ticket"
}

VDV_KAKG_PLACES: typing.Dict[int, str] = {
  1:	"Bundesrepublik gesamt",
  2:	"Baden-Württemberg",
  3:	"Bayern",
  4:	"Berlin",
  5:	"Brandenburg",
  6:	"Bremen",
  7:	"Hamburg",
  8:	"Hessen",
  9:	"Mecklenburg-Vorpommern",
  10:	"Niedersachsen",
  11:	"Nordrhein-Westfalen",
  12:	"Rheinland-Pfalz",
  13:	"Saarland",
  14:	"Sachsen",
  15:	"Sachsen-Anhalt",
  16:	"Schleswig-Holstein",
  17:	"Thüringen"
}