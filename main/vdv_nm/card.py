import dataclasses
from . import fci, application_directory
from .. import vdv

@dataclasses.dataclass
class Card:
    fci: fci.FCI
    application_directory: application_directory.ApplicationDirectory
    ca_cert: vdv.Certificate
    application_cert: vdv.Certificate

    @staticmethod
    def root_ca_data():
        pki_store = vdv.CertificateStore()
        pki_store.load_certificates()
        raw_root_ca = pki_store.find_certificate(vdv.CAReference.root())
        root_ca = vdv.Certificate.parse(raw_root_ca.data)
        assert not root_ca.needs_ca_key()
        root_ca_data = vdv.CertificateData.parse(root_ca)
        assert root_ca_data.ca_reference == vdv.CAReference.root()
        assert root_ca_data.certificate_holder_reference == vdv.CAReference.root()

        return root_ca_data

    def verify_root_ca(self):
        pki_store = vdv.CertificateStore()
        pki_store.load_certificates()
        raw_root_ca = pki_store.find_certificate(vdv.CAReference.root())
        root_ca = vdv.Certificate.parse(raw_root_ca.data)

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
