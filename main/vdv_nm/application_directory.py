import dataclasses
import typing
import ber_tlv.tlv
from .. import vdv
from .util import VDVNMException

@dataclasses.dataclass
class ApplicationDirectory:
    application_data: "ApplicationData"
    application_logbook: "ApplicationLogbook"
    customer_data: "CustomerData"
    key_register: "KeyRegister"
    last_transaction: "LastTransaction"
    priorities: "Priorities"
    authorizations: typing.List["Authorization"]

    @classmethod
    def parse(cls, data: bytes) -> "ApplicationDirectory":
        try:
            data = ber_tlv.tlv.Tlv.parse(data)
        except Exception as e:
            raise VDVNMException("Failed to parse Application Directory") from e

        application_directory = next(filter(lambda t: t[0] == 0xE0, data), None)
        if not application_directory:
            raise VDVNMException("Not an Application Directory")
        application_directory = application_directory[1]

        application_data = next(filter(lambda t: t[0] == 0xE2, application_directory), None)
        if not application_data:
            raise VDVNMException("Missing application data")
        application_data = application_data[1]

        application_logbook = next(filter(lambda t: t[0] == 0xE4, application_directory), None)
        if not application_logbook:
            raise VDVNMException("Missing application logbook")
        application_logbook = application_logbook[1]

        customer_data = next(filter(lambda t: t[0] == 0xE7, application_directory), None)
        if not customer_data:
            raise VDVNMException("Missing customer data")
        customer_data = customer_data[1]

        key_register = next(filter(lambda t: t[0] == 0xEC, application_directory), None)
        if not key_register:
            raise VDVNMException("Missing key register")
        key_register = key_register[1]

        last_transaction = next(filter(lambda t: t[0] == 0xC3, application_directory), None)
        if not last_transaction:
            raise VDVNMException("Missing last transaction")
        last_transaction = last_transaction[1]

        priorities = next(filter(lambda t: t[0] == 0x90, application_directory), None)
        if not priorities:
            raise VDVNMException("Missing priorities")
        priorities = priorities[1]

        authorizations = [Authorization.parse(d[1]) for d in filter(lambda t: t[0] == 0xE9, application_directory)]

        return cls(
            application_data=ApplicationData.parse(application_data),
            application_logbook=ApplicationLogbook.parse(application_logbook),
            customer_data=CustomerData.parse(customer_data),
            key_register=KeyRegister.parse(key_register),
            last_transaction=LastTransaction.parse(last_transaction),
            priorities=Priorities.parse(priorities),
            authorizations=authorizations,
        )

@dataclasses.dataclass
class ApplicationData:
    data_pointer: int
    application_instance_number: int
    application_instance_org_id: int
    app_version: int
    valid_from: vdv.util.DateTime
    valid_to: vdv.util.DateTime
    app_status: int
    app_synchronization_number: int

    def application_instance_org_name(self):
        return vdv.ticket.map_org_id(self.application_instance_org_id)

    def application_instance_org_name_opt(self):
        return vdv.ticket.map_org_id(self.application_instance_org_id, True)

    @classmethod
    def parse(cls, data) -> "ApplicationData":
        system_specific_data = next(filter(lambda t: t[0] == 0xC0, data), None)
        if not system_specific_data:
            raise VDVNMException("Missing system specific data")
        system_specific_data = system_specific_data[1]

        if len(system_specific_data) != 1:
            raise VDVNMException("Invalid system specific data")

        static_data = next(filter(lambda t: t[0] == 0x81, data), None)
        if not static_data:
            raise VDVNMException("Missing application static data")
        static_data = static_data[1]

        if len(static_data) != 15:
            raise VDVNMException("Invalid application static data")

        dynamic_data = next(filter(lambda t: t[0] == 0x80, data), None)
        if not dynamic_data:
            raise VDVNMException("Missing application dynamic data")
        dynamic_data = dynamic_data[1]

        if len(dynamic_data) != 2:
            raise VDVNMException("Invalid application dynamic data")

        return cls(
            data_pointer=system_specific_data[0],
            application_instance_number=int.from_bytes(static_data[0:4], "big"),
            application_instance_org_id=int.from_bytes(static_data[4:6], "big"),
            app_version=static_data[6],
            valid_from=vdv.util.DateTime.from_bytes(static_data[7:11]),
            valid_to=vdv.util.DateTime.from_bytes(static_data[11:15]),
            app_status=dynamic_data[0],
            app_synchronization_number=dynamic_data[1],
        )

@dataclasses.dataclass
class ApplicationLogbook:
    data_pointer: int
    sequence_number: int

    @classmethod
    def parse(cls, data) -> "ApplicationLogbook":
        system_specific_data = next(filter(lambda t: t[0] == 0xC0, data), None)
        if not system_specific_data:
            raise VDVNMException("Missing system specific data")
        system_specific_data = system_specific_data[1]

        if len(system_specific_data) != 1:
            raise VDVNMException("Invalid system specific data")

        static_data = next(filter(lambda t: t[0] == 0x82, data), None)
        if not static_data:
            raise VDVNMException("Missing logbook static data")
        static_data = static_data[1]

        if len(static_data) != 2:
            raise VDVNMException("Invalid logbook static data")

        return cls(
            data_pointer=system_specific_data[0],
            sequence_number=int.from_bytes(static_data[0:2], "big"),
        )

@dataclasses.dataclass
class CustomerData:
    data_pointer: int

    @classmethod
    def parse(cls, data) -> "CustomerData":
        system_specific_data = next(filter(lambda t: t[0] == 0xC0, data), None)
        if not system_specific_data:
            raise VDVNMException("Missing system specific data")
        system_specific_data = system_specific_data[1]

        if len(system_specific_data) != 1:
            raise VDVNMException("Invalid system specific data")

        return cls(
            data_pointer=system_specific_data[0],
        )

@dataclasses.dataclass
class KeyRegister:
    data_pointer: int
    manufacturer_org_id: int
    spec_version: str
    manufacturer_version_number: bytes
    app_instance_id: int
    random_data: bytes
    rfu: bytes

    @classmethod
    def parse(cls, data) -> "KeyRegister":
        system_specific_data = next(filter(lambda t: t[0] == 0xC0, data), None)
        if not system_specific_data:
            raise VDVNMException("Missing system specific data")
        system_specific_data = system_specific_data[1]

        if len(system_specific_data) != 1:
            raise VDVNMException("Invalid system specific data")

        static_data = next(filter(lambda t: t[0] == 0x86, data), None)
        if not static_data:
            raise VDVNMException("Missing key register static data")
        static_data = static_data[1]

        try:
            version_data = ber_tlv.tlv.Tlv.parse(static_data[:10], False)
        except Exception as e:
            raise VDVNMException("Invalid key register static data") from e

        version_data = next(filter(lambda t: t[0] == 0x80, version_data), None)
        if not version_data:
            raise VDVNMException("Missing key register version data")
        version_data = version_data[1]

        if len(version_data) != 8:
            raise VDVNMException("Invalid key register version data")

        static_data = static_data[10:]
        if len(static_data) != 10:
            raise VDVNMException("Invalid key register static data")

        dynamic_data = next(filter(lambda t: t[0] == 0x87, data), None)
        if not dynamic_data:
            raise VDVNMException("Missing key register dynamic data")
        dynamic_data = dynamic_data[1]

        if len(dynamic_data) != 2:
            raise VDVNMException("Invalid key register dynamic data")

        return cls(
            data_pointer=system_specific_data[0],
            manufacturer_org_id=int.from_bytes(version_data[0:2], "big"),
            spec_version=vdv.util.parse_version_number(version_data[2:4]),
            manufacturer_version_number=version_data[4:8],
            app_instance_id=int.from_bytes(static_data[0:6], "big"),
            random_data=static_data[6:10],
            rfu=dynamic_data,
        )

@dataclasses.dataclass
class LastTransaction:
    transaction_type: int
    data_pointer: int

    @classmethod
    def parse(cls, data) -> "LastTransaction":
        if len(data) != 2:
            raise VDVNMException("Invalid last transaction data")

        return cls(
            transaction_type=data[0],
            data_pointer=data[1],
        )

@dataclasses.dataclass
class Priorities:
    data_pointers: typing.List[int]

    @classmethod
    def parse(cls, data) -> "Priorities":
        return cls(
            data_pointers=[p for p in data if p != 0],
        )

@dataclasses.dataclass
class Authorization:
    data_pointer: int
    authorization_id: int
    authorization_org_id: int
    product_id: int
    product_org_id: int
    product_key_org_id: int
    valid_from: vdv.util.DateTime
    valid_to: vdv.util.DateTime
    status: int
    synchronization_number: int

    def authorization_org_name(self):
        return vdv.ticket.map_org_id(self.authorization_org_id)

    def authorization_org_name_opt(self):
        return vdv.ticket.map_org_id(self.authorization_org_id, True)

    def product_name(self, opt=False):
        return vdv.ticket.product_name(self.product_org_id, self.product_id, opt=opt)

    def product_name_opt(self):
        return self.product_name(True)

    def product_org_name(self):
        return vdv.ticket.map_org_id(self.product_org_id)

    def product_org_name_opt(self):
        return vdv.ticket.map_org_id(self.product_org_id, True)

    @classmethod
    def parse(cls, data) -> "Authorization":
        system_specific_data = next(filter(lambda t: t[0] == 0xC0, data), None)
        if not system_specific_data:
            raise VDVNMException("Missing system specific data")
        system_specific_data = system_specific_data[1]

        if len(system_specific_data) != 1:
            raise VDVNMException("Invalid system specific data")

        static_data = next(filter(lambda t: t[0] == 0x83, data), None)
        if not static_data:
            raise VDVNMException("Missing authorization static data")
        static_data = static_data[1]

        if len(static_data) != 20:
            raise VDVNMException("Invalid authorization static data")

        dynamic_data = next(filter(lambda t: t[0] == 0x84, data), None)
        if not dynamic_data:
            raise VDVNMException("Missing authorization dynamic data")
        dynamic_data = dynamic_data[1]

        if len(dynamic_data) != 2:
            raise VDVNMException("Invalid authorization dynamic data")

        return cls(
            data_pointer=system_specific_data[0],
            authorization_id=int.from_bytes(static_data[0:4], "big"),
            authorization_org_id=int.from_bytes(static_data[4:6], "big"),
            product_id=int.from_bytes(static_data[6:8], "big"),
            product_org_id=int.from_bytes(static_data[8:10], "big"),
            product_key_org_id=int.from_bytes(static_data[10:12], "big"),
            valid_from=vdv.util.DateTime.from_bytes(static_data[12:16]),
            valid_to=vdv.util.DateTime.from_bytes(static_data[16:20]),
            status=dynamic_data[0],
            synchronization_number=dynamic_data[1],
        )
