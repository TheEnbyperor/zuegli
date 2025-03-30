import dataclasses
from . import fci, application_directory, application_data
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

@dataclasses.dataclass
class Card:
    fci: fci.FCI
    application_directory: application_directory.ApplicationDirectory
    application_data: application_data.ApplicationData
    ca_cert: vdv.Certificate
    application_cert: vdv.Certificate

    def root_ca_data(self):
        pki_store = get_pki()
        raw_root_ca = pki_store.find_certificate(self.ca_cert_data().ca_reference)
        if not raw_root_ca:
            return None
        root_ca = vdv.Certificate.parse(raw_root_ca.data)
        root_ca_data = vdv.CertificateData.parse(root_ca)

        return root_ca_data

    def verify_root_ca(self):
        pki_store = get_pki()
        raw_root_ca = pki_store.find_certificate(self.ca_cert_data().ca_reference)
        if not raw_root_ca:
            return False
        root_ca = vdv.Certificate.parse(raw_root_ca.data)

        try:
            root_ca.verify_signature(self.root_ca_data())
        except vdv.VDVException:
            return False
        return True

    def verify_ca_cert(self):
        root_ca_data = self.root_ca_data()
        if not root_ca_data:
            return False

        try:
            self.ca_cert.verify_signature(root_ca_data)
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
