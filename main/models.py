import base64
import secrets
import dacite
import datetime
from django.utils import timezone
from django.shortcuts import reverse
from django.conf import settings
from django.db import models
from django.core import validators
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from . import ticket as t
from . import vdv_nm
from . import vdv, uic, rsp, sncf, elb, ssb, ssb1, hzpp, swisspass, iata, bahnbonus


def make_pass_token():
    return secrets.token_urlsafe(32)


class Account(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    db_token = models.TextField(null=True, blank=True, verbose_name="Deutsche Bahn bearer token")
    db_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Deutsche Bahn bearer token expiration")
    db_refresh_token = models.TextField(null=True, blank=True, verbose_name="Deutsche Bahn refresh token")
    db_refresh_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Deutsche Bahn refresh token expiration")
    db_account_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Deutsche Bahn Account ID")
    bahnbonus_token = models.TextField(null=True, blank=True, verbose_name="BahnBonus bearer token")
    bahnbonus_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="BahnBonus bearer token expiration")
    bahnbonus_refresh_token = models.TextField(null=True, blank=True, verbose_name="BahnBonus refresh token")
    bahnbonus_refresh_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="BahnBonus refresh token expiration")
    avv_token = models.TextField(null=True, blank=True, verbose_name="AVV Bearer token")
    avv_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="AVV Bearer token expiration")
    avv_refresh_token = models.TextField(null=True, blank=True, verbose_name="AVV Refresh token")
    avv_refresh_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="AVV Rrefresh token expiration")
    avv_device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="AVV Device ID")
    saarvv_token = models.TextField(null=True, blank=True, verbose_name="SaarVV Token")
    saarvv_device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="SaarVV Device ID")
    sbahn_berlin_token = models.TextField(null=True, blank=True, verbose_name="S-Bahn Berlin Token")
    sbahn_berlin_device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="S-Bahn Berlin Device ID")
    calendar_token = models.CharField(max_length=255, verbose_name="iCal token", default=make_pass_token)
    nfc_link_token = models.CharField(max_length=255, verbose_name="NFC link token", default=make_pass_token)

    def __str__(self):
        return str(self.user)

    def is_db_authenticated(self) -> bool:
        now = timezone.now()
        if self.db_token and self.db_token_expires_at and self.db_token_expires_at > now:
            return True
        elif self.db_refresh_token and self.db_refresh_token_expires_at and self.db_refresh_token_expires_at > now:
            return True
        else:
            return False

    def is_bahnbonus_authenticated(self) -> bool:
        now = timezone.now()
        if self.bahnbonus_token and self.bahnbonus_token_expires_at and self.bahnbonus_token_expires_at > now:
            return True
        elif self.bahnbonus_refresh_token and self.bahnbonus_refresh_token_expires_at and self.bahnbonus_refresh_token_expires_at > now:
            return True
        else:
            return False

    def is_avv_authenticated(self) -> bool:
        now = timezone.now()
        if self.avv_token and self.avv_token_expires_at and self.avv_token_expires_at > now:
            return True
        elif self.avv_refresh_token and self.avv_refresh_token_expires_at and self.avv_refresh_token_expires_at > now:
            return True
        else:
            return False

    def is_saarvv_authenticated(self) -> bool:
        return bool(self.saarvv_token)

    def is_sbahn_berlin_authenticated(self) -> bool:
        return bool(self.sbahn_berlin_token)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(instance, created, **kwargs):
    if created or not hasattr(instance, "account"):
        Account.objects.create(user=instance)
    instance.account.save()


class Ticket(models.Model):
    TYPE_DEUTCHLANDTICKET = "deutschlandticket"
    TYPE_KLIMATICKET = "klimaticket"
    TYPE_BAHNCARD = "bahncard"
    TYPE_FAHRKARTE = "fahrkarte"
    TYPE_BORDKARTE = "bordkarte"
    TYPE_RESERVIERUNG = "reservierung"
    TYPE_INTERRAIL = "interrail"
    TYPE_RAILCARD = "railcard"
    TYPE_KEYCARD = "keycard"
    TYPE_BAHNBONUS = "bahnbonus"
    TYPE_UNKNOWN = "unknown"

    TICKET_TYPES = (
        (TYPE_DEUTCHLANDTICKET, "Deutschlandticket"),
        (TYPE_KLIMATICKET, "Klimaticket"),
        (TYPE_BAHNCARD, "Bahncard"),
        (TYPE_FAHRKARTE, "Fahrkarte"),
        (TYPE_BORDKARTE, "Bordkarte"),
        (TYPE_RESERVIERUNG, "Reservierung"),
        (TYPE_INTERRAIL, "Interrail"),
        (TYPE_RAILCARD, "Railcard"),
        (TYPE_KEYCARD, "Keycard"),
        (TYPE_BAHNBONUS, "BahnBonus"),
        (TYPE_UNKNOWN, "Unknown"),
    )

    id = models.CharField(max_length=32, primary_key=True, verbose_name="ID")
    ticket_type = models.CharField(max_length=255, choices=TICKET_TYPES, verbose_name="Ticket type", default=TYPE_UNKNOWN)
    pkpass_authentication_token = models.CharField(max_length=255, verbose_name="PKPass authentication token", default=make_pass_token)
    last_updated = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets", db_index=True)
    db_subscription = models.ForeignKey(
        "DBSubscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets", verbose_name="DB Subscription", db_index=True
    )
    saarvv_account = models.ForeignKey(
        "Account", on_delete=models.SET_NULL, null=True, blank=True, related_name="saarvv_tickets", verbose_name="SaarVV Account", db_index=True
    )
    sbahn_berlin_account = models.ForeignKey(
        "Account", on_delete=models.SET_NULL, null=True, blank=True, related_name="sbahn_berlin_tickets", verbose_name="S-Bahn Berlin Account", db_index=True
    )
    avv_account = models.ForeignKey(
        "Account", on_delete=models.SET_NULL, null=True, blank=True, related_name="avv_tickets", verbose_name="AVV Account", db_index=True
    )
    photos = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.get_ticket_type_display()} - {self.id}"

    def get_absolute_url(self):
        return reverse("ticket", kwargs={"pk": self.id})

    def public_id(self):
        return self.pk.upper()[0:8]

    def active_instance(self):
        now = timezone.now()
        if ticket_instance := self.uic_instances.filter(validity_start__lte=now).order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.vdv_instances.filter(validity_start__lte=now).order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.rsp_instances.filter(validity_start__lte=now).order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.uic_instances.filter(
            ~Q(validity_start__lte=now) | Q(validity_start__isnull=True),
        ).order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.vdv_instances.filter(
            ~Q(validity_start__lte=now) | Q(validity_start__isnull=True),
        ).order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.rsp_instances.filter(
            ~Q(validity_start__lte=now) | Q(validity_start__isnull=True),
        ).order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.uic_instances.order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.vdv_instances.order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.rsp_instances.order_by("-validity_end").first():
            return ticket_instance

        if ticket_instance := self.sncf_instances.first():
            return ticket_instance

        if ticket_instance := self.elb_instances.first():
            return ticket_instance

        if ticket_instance := self.ssb_instances.first():
            return ticket_instance

        if ticket_instance := self.ssb1_instances.first():
            return ticket_instance

        if ticket_instance := self.hzpp_instances.first():
            return ticket_instance

        if ticket_instance := self.swisspass_instances.first():
            return ticket_instance

        if ticket_instance := self.iata_instances.first():
            return ticket_instance

        if ticket_instance := self.bahnbonus_instances.first():
            return ticket_instance

        return None


class AccessLogEntry(models.Model):
    ACTION_UPLOAD = "upload"
    ACTION_DOWNLOAD_PKPASS = "download-pkpass"

    ACTIONS = (
        (ACTION_UPLOAD, "Upload ticket barcode"),
        (ACTION_DOWNLOAD_PKPASS, "Download PKPass"),
    )

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="access_logs", db_index=True)
    action = models.CharField(choices=ACTIONS, max_length=255)
    remote_ip = models.GenericIPAddressField()
    headers = models.JSONField(default=dict)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_logs", db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class VDVTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="vdv_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    ticket_org_id = models.PositiveIntegerField(verbose_name="Organization ID", db_index=True)
    validity_start = models.DateTimeField()
    validity_end = models.DateTimeField()
    barcode_data = models.BinaryField()
    decoded_data = models.JSONField()

    class Meta:
        ordering = ["-validity_start"]
        verbose_name = "VDV ticket"

    def __str__(self):
        return f"{self.ticket_org_id} - {self.barcode_hash}"

    def as_ticket(self) -> t.VDVTicket:
        config = dacite.Config(type_hooks={
            bytes: base64.b64decode,
            datetime.datetime: datetime.datetime.fromisoformat,
            datetime.date: datetime.date.fromisoformat,
            vdv.pki.ECDSACurve: vdv.pki.ECDSACurve,
        })
        raw_ticket = base64.b64decode(self.decoded_data["ticket"])

        return t.VDVTicket(
            root_ca=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["root_ca"], config=config),
            issuing_ca=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["issuing_ca"], config=config),
            envelope_certificate=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["envelope_certificate"], config=config),
            raw_ticket=raw_ticket,
            ticket=vdv.VDVTicket.parse(raw_ticket, vdv.ticket.Context(
                account_forename=self.ticket.account.user.first_name if self.ticket.account else None,
                account_surname=self.ticket.account.user.last_name if self.ticket.account else None,
                email=self.ticket.account.user.email if self.ticket.account else None,
            )),
            motics=dacite.from_dict(data_class=vdv.Motics, data=self.decoded_data["motics"], config=config) if self.decoded_data.get("motics") else None,
        )


class UICTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="uic_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    distributor_rics = models.PositiveIntegerField(validators=[validators.MaxValueValidator(9999)], verbose_name="Distributor RICS", db_index=True)
    issuing_time = models.DateTimeField()
    barcode_data = models.BinaryField()
    decoded_data = models.JSONField()
    validity_start = models.DateTimeField(blank=True, null=True)
    validity_end = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-issuing_time"]
        verbose_name = "UIC ticket"

    def __str__(self):
        return f"{self.distributor_rics} - {self.barcode_hash}"

    def as_ticket(self) -> t.UICTicket:
        config = dacite.Config(type_hooks={
            bytes: base64.b64decode,
            datetime.datetime: datetime.datetime.fromisoformat,
            datetime.date: datetime.date.fromisoformat,
        })
        context = vdv.ticket.Context(
            account_forename=self.ticket.account.user.first_name if self.ticket.account else None,
            account_surname=self.ticket.account.user.last_name if self.ticket.account else None,
            email=self.ticket.account.user.email if self.ticket.account else None,
        )

        if self.decoded_data.get("envelope"):
            ticket_envelope = dacite.from_dict(data_class=uic.Envelope, data=self.decoded_data["envelope"], config=config)
            return t.UICTicket.from_envelope(bytes(self.barcode_data), ticket_envelope, context)
        elif self.decoded_data.get("dosipas_envelope"):
            ticket_envelope = dacite.from_dict(data_class=uic.DOSIPASEnvelope, data=self.decoded_data["dosipas_envelope"], config=config)
            return t.UICTicket.from_dosipas(bytes(self.barcode_data), ticket_envelope, context)
        else:
            raise AssertionError("Unreachable code")


class RSPTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="rsp_instances", db_index=True)
    issuer_id = models.CharField(max_length=2, verbose_name="Issuer ID", db_index=True)
    reference = models.CharField(max_length=20, verbose_name="Ticket reference", db_index=True)
    barcode_data = models.BinaryField()
    ticket_type = models.CharField(max_length=2, verbose_name="Ticket type", default="06")
    decoded_data = models.JSONField()
    validity_start = models.DateTimeField(blank=True, null=True)
    validity_end = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = [
            ("ticket_type", "reference", "issuer_id"),
        ]
        index_together = [
            ("ticket_type", "reference", "issuer_id"),
        ]
        verbose_name = "RSP ticket"

    def __str__(self):
        return f"{self.issuer_id} - {self.reference}"

    def as_ticket(self) -> t.RSPTicket:
        raw_ticket = base64.b64decode(self.decoded_data["raw_ticket"])
        if self.ticket_type == "08":
            data = rsp.RailcardData.parse(raw_ticket)
        elif self.ticket_type == "06":
            data = rsp.TicketData.parse(raw_ticket)
        else:
            raise NotImplementedError()
        return t.RSPTicket(
            rsp_type=self.ticket_type,
            ticket_ref=self.reference,
            issuer_id=self.issuer_id,
            raw_ticket=raw_ticket,
            data=data
        )


class SNCFTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="sncf_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "SNCF ticket"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.SNCFTicket:
        return t.SNCFTicket(
            raw_ticket=self.barcode_data,
            data=sncf.SNCFTicket.parse(bytes(self.barcode_data))
        )


class HZPPTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="hzpp_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "HŽPP ticket"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.HZPPTicket:
        return t.HZPPTicket(
            raw_ticket=self.barcode_data,
            data=hzpp.HZPPTicket.parse(bytes(self.barcode_data))
        )


class ELBTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="elb_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "ELB ticket"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.ELBTicket:
        return t.ELBTicket(
            raw_ticket=bytes(self.barcode_data),
            data=elb.ELBTicket.parse(bytes(self.barcode_data)),
        )


class SSBTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="ssb_instances", db_index=True)
    distributor_rics = models.PositiveIntegerField(validators=[validators.MaxValueValidator(9999)], verbose_name="Distributor RICS", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()
    ssb_data = models.BinaryField(null=True)

    class Meta:
        verbose_name = "SSB ticket"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.SSBTicket:
        envelope = ssb.Envelope.parse(bytes(self.ssb_data or self.barcode_data))
        context = vdv.ticket.Context(
            account_forename=self.ticket.account.user.first_name if self.ticket.account else None,
            account_surname=self.ticket.account.user.last_name if self.ticket.account else None,
            email=self.ticket.account.user.email if self.ticket.account else None,
        )

        if envelope.ticket_type == 1:
            data = ssb.IntegratedReservationTicket.parse(envelope.data, envelope.issuer_rics, context)
        elif envelope.ticket_type == 2:
            data = ssb.NonReservationTicket.parse(envelope.data, envelope.issuer_rics, context)
        elif envelope.ticket_type == 3:
            data = ssb.GroupTicket.parse(envelope.data, envelope.issuer_rics)
        elif envelope.ticket_type == 4:
            data = ssb.Pass.parse(envelope.data)
        elif envelope.issuer_rics == 1184 and envelope.ticket_type == 21:
            data = ssb.ns_keycard.Keycard.parse(envelope.data)
        elif envelope.issuer_rics == 1179 and envelope.ticket_type == 21:
            data = ssb.sz.Ticket.parse(envelope.data)
        else:
            raise NotImplementedError()

        return t.SSBTicket(
            raw_ticket=bytes(self.barcode_data),
            envelope=envelope,
            data=data
        )


class SSB1TicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="ssb1_instances", db_index=True)
    distributor_rics = models.PositiveIntegerField(validators=[validators.MaxValueValidator(9999)], verbose_name="Distributor RICS", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "SSBv1 ticket"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.SSB1Ticket:
        ticket = ssb1.Ticket.parse(bytes(self.barcode_data))

        return t.SSB1Ticket(
            raw_ticket=bytes(self.barcode_data),
            ticket=ticket,
        )


class SwissPassTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="swisspass_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "SwissPass ticket"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.SwissPassTicket:
        return t.SwissPassTicket(
            raw_ticket=self.barcode_data,
            data=swisspass.SwissPassTicket.parse(bytes(self.barcode_data))
        )


class IATATicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="iata_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "IATA ticket"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.IATATicket:
        return t.IATATicket(
            raw_ticket=self.barcode_data,
            data=iata.Envelope.parse(bytes(self.barcode_data))
        )


class BahnBonusInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="bahnbonus_instances", db_index=True)
    barcode_hash = models.CharField(unique=True, max_length=64, db_index=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "BahnBonus code"

    def __str__(self):
        return str(self.barcode_hash)

    def as_ticket(self) -> t.BahnBonusCode:
        return t.BahnBonusCode(
            raw_ticket=self.barcode_data,
            data=bahnbonus.BahnBonusCode.parse(bytes(self.barcode_data))
        )


class AppleDevice(models.Model):
    device_id = models.CharField(max_length=255, primary_key=True, verbose_name="Device ID")
    push_token = models.CharField(max_length=255, verbose_name="Push token")

    def __str__(self):
        return self.device_id

    def accounts(self):
        accounts = []
        for reg in self.registrations.all():
            if reg.ticket.account_id:
                accounts.append(reg.ticket.account_id)
        return accounts


class AppleRegistration(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="apple_registrations", db_index=True)
    device = models.ForeignKey(AppleDevice, on_delete=models.CASCADE, related_name="registrations", db_index=True)
    ticket_part = models.CharField(max_length=255, verbose_name="Ticket part", blank=True, null=True)

    class Meta:
        unique_together = [
            ["ticket", "device", "ticket_part"],
        ]


class DBSubscription(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="subscriptions", db_index=True)
    device_token = models.CharField(max_length=255, verbose_name="Device token", unique=True)
    refresh_at = models.DateTimeField(verbose_name="Refresh at")
    info = models.JSONField(verbose_name="Info", default=dict)

    class Meta:
        verbose_name = "DB Subscription"
        verbose_name_plural = "DB Subscriptions"

    def __str__(self):
        return str(self.device_token)

    def get_current_info(self):
        if "type" not in self.info:
            return None

        if self.info["type"] == "VendoHuelle":
            return self.info
        elif self.info["type"] == "TicketHuelle":
            now = timezone.now()
            for info in self.info["ticketHuellen"]:
                start = datetime.datetime.fromisoformat(info["anzeigeAb"])
                end = datetime.datetime.fromisoformat(info["anzeigeBis"])
                if start > now and end < now:
                    return info["huelleInfo"]

        return None


class ZHVStop(models.Model):
    dhid = models.CharField(max_length=255, verbose_name="DHID", primary_key=True)
    dhid_raw_id = models.CharField(max_length=255, verbose_name="DHID raw ID")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="children", db_constraint=False, blank=True, null=True)
    name = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    description = models.TextField(blank=True, null=True)
    municipality = models.TextField(blank=True, null=True)
    district = models.TextField(blank=True, null=True)
    authority = models.CharField(max_length=255, db_index=True)
    thid = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["dhid_raw_id", "authority"]),
        ]


class VDVSmartcard(models.Model):
    id = models.CharField(max_length=32, primary_key=True, verbose_name="ID")
    last_updated = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="vdv_smartcards", db_index=True)
    atr_identifier = models.BinaryField()
    atr_historical_bytes = models.BinaryField()
    atr_application_data = models.BinaryField()
    fci = models.BinaryField()
    application_directory = models.BinaryField()
    ca_cert = models.BinaryField()
    application_cert = models.BinaryField()
    application_data = models.BinaryField()
    application_info_text = models.TextField(blank=True, null=False)
    key_register = models.BinaryField()
    customer_info_text = models.TextField(blank=True, null=False)

    class Meta:
        verbose_name = "VDV Smartcard"
        verbose_name_plural = "VDV Smartcards"

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        return reverse("vdv_smartcard", kwargs={"pk": self.id})

    def public_id(self):
        return self.pk.upper()[0:8]

    def as_card(self) -> vdv_nm.card.Card:
        return vdv_nm.card.Card(
            fci=vdv_nm.fci.FCI.parse(bytes(self.fci)),
            application_directory=vdv_nm.application_directory.ApplicationDirectory.parse(bytes(self.application_directory)),
            application_data=vdv_nm.application_data.ApplicationData.parse(bytes(self.application_data)),
            ca_cert=vdv.Certificate.parse(bytes(self.ca_cert)),
            application_cert=vdv.Certificate.parse(bytes(self.application_cert)),
        )

class VDVSmartcardLog(models.Model):
    smartcard = models.ForeignKey(VDVSmartcard, on_delete=models.CASCADE, related_name="logs", db_index=True)
    sequence_number = models.IntegerField()
    log_entry = models.BinaryField()

    class Meta:
        verbose_name = "VDV Smartcard Log Entry"
        verbose_name_plural = "VDV Smartcard Log Entries"
        unique_together = [("smartcard", "sequence_number")]

    def __str__(self):
        return f"{self.smartcard} #{self.sequence_number}"

    def as_log(self) -> vdv_nm.log.LogEntry:
        return vdv_nm.log.parse_log(bytes(self.log_entry))
