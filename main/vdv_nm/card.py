import dataclasses
from . import fci, application_directory
from .. import vdv

PKI_STORE = None
ROOT_CA = None

def get_pki():
    global PKI_STORE

    if PKI_STORE is not None:
        return PKI_STORE

    pki_store = vdv.CertificateStore()
    pki_store.load_certificates()
    PKI_STORE = pki_store

    return pki_store

def get_root_ca():
    global ROOT_CA

    if ROOT_CA is not None:
        return ROOT_CA

    pki_store = get_pki()
    raw_root_ca = pki_store.find_certificate(vdv.CAReference.root())

    ROOT_CA = vdv.Certificate.parse(raw_root_ca.data)

    return ROOT_CA

@dataclasses.dataclass
class Card:
    fci: fci.FCI
    application_directory: application_directory.ApplicationDirectory
    ca_cert: vdv.Certificate
    application_cert: vdv.Certificate

    @staticmethod
    def root_ca_data():
        root_ca = get_root_ca()
        assert not root_ca.needs_ca_key()
        root_ca_data = vdv.CertificateData.parse(root_ca)
        assert root_ca_data.ca_reference == vdv.CAReference.root()
        assert root_ca_data.certificate_holder_reference == vdv.CAReference.root()

        return root_ca_data

    def verify_root_ca(self):
        root_ca = get_root_ca()

        try:
            root_ca.verify_signature(self.root_ca_data())
        except vdv.VDVException:
            return False
        return True

    def verify_ca_cert(self):
        try:
            self.ca_cert.verify_signature(self.root_ca_data())
        except vdv.VDVException:
            return False
        return True

    def ca_cert_data(self):
        return vdv.CertificateData.parse(self.ca_cert)

    def verify_application_cert(self):
        try:
            self.application_cert.verify_signature(self.ca_cert_data())
        except vdv.VDVException:
            return False
        return True

    def application_cert_data(self):
        return vdv.CertificateData.parse(self.application_cert)
