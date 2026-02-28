import secrets
import traceback
import base64
import datetime
import Crypto.Hash.TupleHash128
import ber_tlv.tlv
from django.conf import settings
from .. import vdv_nm, vdv, models
from . import iso7816


class VDVConsumer(iso7816.Consumer):
    def acceptable_aids(self):
        return [vdv_nm.util.VDV_KA_NM_AID]

    def get_entitlement(self, data_pointer: int):
        sam_challenge = secrets.token_bytes(8)
        data = ber_tlv.tlv.Tlv.build({
            0x80: sam_challenge,
        })
        resp = self.apdu(iso7816.RequestAPDU(
            instruction_class=0x80, instruction=0x54, p1=0x00, p2=data_pointer,
            data=data, expected_response_length=256,
        ))
        if not resp.is_success():
            return None
        return vdv_nm.get_entitlement.GetEntitlement.parse(resp.data, sam_challenge)

    def run(self):
        try:
            self.message("Reading card metadata...")
            fci_data = self.select_application_by_aid(vdv_nm.util.VDV_KA_NM_AID)
            if not fci_data.is_success():
                self.error("Failed to read File Control Information")
                return

            vdv_nm.fci.FCI.parse(fci_data.data)

            self.message("Reading card directory...")
            application_directory_data = self.apdu(iso7816.RequestAPDU(
                instruction_class=0x00, instruction=0xA4, p1=0x04, p2=0x0C,
                data=vdv_nm.util.VDV_KA_NM_AID, expected_response_length=256,
            ))
            if not application_directory_data.is_success():
                self.error("Failed to read Application Directory")
                return

            application_directory = vdv_nm.application_directory.ApplicationDirectory.parse(
                application_directory_data.data)

            hd = Crypto.Hash.TupleHash128.new(digest_bytes=16)
            hd.update(b"vdv-ka-nm")
            hd.update(application_directory.application_data.application_instance_org_id.to_bytes(8, "big"))
            hd.update(application_directory.application_data.application_instance_number.to_bytes(8, "big"))
            card_id = base64.b32hexencode(hd.digest()).decode("utf-8")

            self.message("Reading data files...")
            application_data_data = self.apdu(iso7816.RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                data=bytes([0xEE, application_directory.application_data.data_pointer]),
                expected_response_length=256,
            ))
            if not application_data_data:
                self.error("Failed to read Application Data")
                return
            vdv_nm.application_data.ApplicationData.parse(application_data_data.data)

            application_info_text_data = self.apdu(iso7816.RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                data=bytes([0xC7, application_directory.application_data.data_pointer]),
                expected_response_length=256,
            ))
            if not application_info_text_data.is_success():
                self.error("Failed to read Application Info Text")

            application_info_text = vdv_nm.info_text.InfoText.parse(application_info_text_data.data)

            log_entries = []
            for i in range(1, min(application_directory.application_logbook.sequence_number, 10) + 1):
                application_logbook = self.apdu(iso7816.RequestAPDU(
                    instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                    data=bytes([0xE5, i]),
                    expected_response_length=256,
                ))
                if not application_logbook.is_success():
                    self.error(f"Failed to read Application Logbook {i}")
                log_entry = vdv_nm.log.parse_log(application_logbook.data)
                log_entries.append((log_entry, application_logbook.data))

            key_register = self.apdu(iso7816.RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                data=bytes([0xED, application_directory.key_register.data_pointer]),
                expected_response_length=256,
            ))
            if not key_register.is_success():
                self.error("Failed to read Key Register")

            vdv_nm.key_register.KeyRegister.parse(key_register.data)

            customer_infotext = self.apdu(iso7816.RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                data=bytes([0xC7, application_directory.customer_data.data_pointer]),
                expected_response_length=256,
            ))
            if not customer_infotext.is_success():
                self.error("Failed to read Customer Info Text")
            customer_infotext = vdv_nm.info_text.InfoText.parse(customer_infotext.data)

            self.message("Reading travel authorizations...")
            authorizations = []
            for auth in application_directory.authorizations:
                authorization_data = self.apdu(iso7816.RequestAPDU(
                    instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                    data=bytes([0xEA, auth.data_pointer]),
                    expected_response_length=256,
                ))
                if not authorization_data.is_success():
                    self.error("Failed to read Authorization Data")
                vdv_nm.authorization.Authorization.parse(authorization_data.data)

                authorization_infotext = self.apdu(iso7816.RequestAPDU(
                    instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0xF0,
                    data=bytes([0xC7, auth.data_pointer]),
                    expected_response_length=256,
                ))
                if not authorization_infotext.is_success():
                    self.error("Failed to read Authorization Info Text")
                authorization_infotext = vdv_nm.info_text.InfoText.parse(authorization_infotext.data)
                authorizations.append((authorization_data.data, auth, authorization_infotext.text))

            self.message("Reading public keys...")

            ca_pk_bytes = bytearray()
            ca_pk_data = self.apdu(iso7816.RequestAPDU(
                instruction_class=0x10, instruction=0xCA, p1=0x01, p2=0x12,
                data=b"", expected_response_length=256,
            ))
            if not ca_pk_data.is_success():
                self.error("Failed to read CA Certificate")
            while len(ca_pk_data.data) == 256:
                ca_pk_bytes.extend(ca_pk_data.data)
                ca_pk_data = self.apdu(iso7816.RequestAPDU(
                    instruction_class=0x10, instruction=0xCA, p1=0x01, p2=0x12,
                    data=b"", expected_response_length=256,
                ))
                if not ca_pk_data.is_success():
                    self.error("Failed to read CA Certificate")
            self.apdu(iso7816.RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0x12,
                data=b"", expected_response_length=256,
            ))
            ca_pk_bytes.extend(ca_pk_data.data)

            ca_pk = vdv.Certificate.parse(ca_pk_bytes)
            vdv.CertificateData.parse(ca_pk)

            application_pk_bytes = bytearray()
            application_pk_data = self.apdu(iso7816.RequestAPDU(
                instruction_class=0x10, instruction=0xCA, p1=0x01, p2=0x11,
                data=b"", expected_response_length=256,
            ))
            if not application_pk_data.is_success():
                self.error("Failed to read Application Certificate")
                return
            while len(application_pk_data.data) == 256:
                application_pk_bytes.extend(application_pk_data.data)
                application_pk_data = self.apdu(iso7816.RequestAPDU(
                    instruction_class=0x10, instruction=0xCA, p1=0x01, p2=0x11,
                    data=b"", expected_response_length=256,
                ))
                if not application_pk_data.is_success():
                    self.error("Failed to read Application Certificate")
            self.apdu(iso7816.RequestAPDU(
                instruction_class=0x00, instruction=0xCA, p1=0x01, p2=0x11,
                data=b"", expected_response_length=256,
            ))
            application_pk_bytes.extend(application_pk_data.data)

            application_pk = vdv.Certificate.parse(application_pk_bytes)
            vdv.CertificateData.parse(application_pk)

            self.message("Saving...")

            d = {
                "atr_identifier": self.identifier,
                "atr_historical_bytes": self.historical_bytes,
                "atr_application_data": self.application_data,
                "last_updated": datetime.datetime.now(),
                "fci": fci_data.data,
                "application_directory": application_directory_data.data,
                "ca_cert": ca_pk_bytes,
                "application_cert": application_pk_bytes,
                "application_data": application_data_data.data,
                "application_info_text": application_info_text.text,
                "key_register": key_register.data,
                "customer_info_text": customer_infotext.text,
            }
            if self.account:
                d["account"] = self.account
            card, _ = models.VDVSmartcard.objects.update_or_create(
                id=card_id,
                defaults=d
            )

            for entry, data in log_entries:
                models.VDVSmartcardLog.objects.update_or_create(
                    smartcard=card,
                    sequence_number=entry.general.sequence_number,
                    defaults={
                        "log_entry": data
                    }
                )

            for data, auth, info_text in authorizations:
                models.VDVSmartcardAuthorization.objects.update_or_create(
                    smartcard=card,
                    authorization_number=auth.authorization_id,
                    authorization_org_id=auth.authorization_org_id,
                    defaults={
                        "authorization": data,
                        "info_text": info_text
                    }
                )
                pass

            self.done(f"{settings.EXTERNAL_URL_BASE}{card.get_absolute_url()}")
        except (vdv_nm.VDVNMException, vdv.VDVException) as e:
            traceback.print_exc()
            self.error(str(e))
