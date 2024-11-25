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
from . import vdv, uic, rsp, sncf, elb, ssb


def make_pass_token():
    return secrets.token_urlsafe(32)


class Account(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    db_token = models.TextField(null=True, blank=True, verbose_name="Deutsche Bahn Bearer token")
    db_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Deutsche Bahn Bearer token expiration")
    db_refresh_token = models.TextField(null=True, blank=True, verbose_name="Deutsche Bahn refresh token")
    db_refresh_token_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Deutsche Bahn refresh token expiration")
    db_account_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Deutsche Bahn Account ID")
    saarvv_token = models.TextField(null=True, blank=True, verbose_name="SaarVV Token")
    saarvv_device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="SaarVV Device ID")

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

    def is_saarvv_authenticated(self) -> bool:
        return bool(self.saarvv_token)


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
    TYPE_RESERVIERUNG = "reservierung"
    TYPE_INTERRAIL = "interrail"
    TYPE_RAILCARD = "railcard"
    TYPE_KEYCARD = "keycard"
    TYPE_UNKNOWN = "unknown"

    TICKET_TYPES = (
        (TYPE_DEUTCHLANDTICKET, "Deutschlandticket"),
        (TYPE_KLIMATICKET, "Klimaticket"),
        (TYPE_BAHNCARD, "Bahncard"),
        (TYPE_FAHRKARTE, "Fahrkarte"),
        (TYPE_RESERVIERUNG, "Reservierung"),
        (TYPE_INTERRAIL, "Interrail"),
        (TYPE_RAILCARD, "Railcard"),
        (TYPE_KEYCARD, "Keycard"),
        (TYPE_UNKNOWN, "Unknown"),
    )

    id = models.CharField(max_length=32, primary_key=True, verbose_name="ID")
    ticket_type = models.CharField(max_length=255, choices=TICKET_TYPES, verbose_name="Ticket type", default=TYPE_UNKNOWN)
    pkpass_authentication_token = models.CharField(max_length=255, verbose_name="PKPass authentication token", default=make_pass_token)
    last_updated = models.DateTimeField()
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")
    db_subscription = models.ForeignKey(
        "DBSubscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets", verbose_name="DB Subscription"
    )
    saarvv_account = models.ForeignKey(
        "Account", on_delete=models.SET_NULL, null=True, blank=True, related_name="saarvv_tickets"
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


class VDVTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="vdv_instances")
    ticket_number = models.PositiveIntegerField(verbose_name="Ticket number")
    ticket_org_id = models.PositiveIntegerField(verbose_name="Organization ID")
    validity_start = models.DateTimeField()
    validity_end = models.DateTimeField()
    barcode_data = models.BinaryField()
    decoded_data = models.JSONField()

    class Meta:
        unique_together = [
            ["ticket_number", "ticket_org_id"],
        ]
        ordering = ["-validity_start"]
        verbose_name = "VDV ticket"

    def __str__(self):
        return f"{self.ticket_org_id} - {self.ticket_number}"

    def as_ticket(self) -> t.VDVTicket:
        config = dacite.Config(type_hooks={bytes: base64.b64decode})
        raw_ticket = base64.b64decode(self.decoded_data["ticket"])

        return t.VDVTicket(
            root_ca=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["root_ca"], config=config),
            issuing_ca=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["issuing_ca"], config=config),
            envelope_certificate=dacite.from_dict(data_class=vdv.CertificateData, data=self.decoded_data["envelope_certificate"], config=config),
            raw_ticket=raw_ticket,
            ticket=vdv.VDVTicket.parse(raw_ticket, vdv.ticket.Context(
                account_forename=self.ticket.account.user.first_name if self.ticket.account else None,
                account_surname=self.ticket.account.user.last_name if self.ticket.account else None,
            ))
        )


class UICTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="uic_instances")
    reference = models.CharField(max_length=20, verbose_name="Ticket ID")
    distributor_rics = models.PositiveIntegerField(validators=[validators.MaxValueValidator(9999)], verbose_name="Distributor RICS")
    issuing_time = models.DateTimeField()
    barcode_data = models.BinaryField()
    decoded_data = models.JSONField()
    validity_start = models.DateTimeField(blank=True, null=True)
    validity_end = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = [
            ["reference", "distributor_rics"],
        ]
        ordering = ["-issuing_time"]
        verbose_name = "UIC ticket"

    def __str__(self):
        return f"{self.distributor_rics} - {self.reference}"

    def as_ticket(self) -> t.UICTicket:
        config = dacite.Config(type_hooks={bytes: base64.b64decode})
        context = vdv.ticket.Context(
            account_forename=self.ticket.account.user.first_name if self.ticket.account else None,
            account_surname=self.ticket.account.user.last_name if self.ticket.account else None,
        )

        ticket_envelope = dacite.from_dict(data_class=uic.Envelope, data=self.decoded_data["envelope"], config=config)
        return t.UICTicket.from_envelope(bytes(self.barcode_data), ticket_envelope, context)


class RSPTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="rsp_instances")
    issuer_id = models.CharField(max_length=2, verbose_name="Issuer ID")
    reference = models.CharField(max_length=20, verbose_name="Ticket reference")
    barcode_data = models.BinaryField()
    ticket_type = models.CharField(max_length=2, verbose_name="Ticket type", default="06")
    decoded_data = models.JSONField()
    validity_start = models.DateTimeField(blank=True, null=True)
    validity_end = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = [
            ["ticket_type", "reference", "issuer_id"],
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
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="sncf_instances")
    reference = models.CharField(max_length=20, verbose_name="Ticket number", unique=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "SNCF ticket"

    def __str__(self):
        return str(self.reference)

    def as_ticket(self) -> t.SNCFTicket:
        return t.SNCFTicket(
            raw_ticket=self.barcode_data,
            data=sncf.SNCFTicket.parse(bytes(self.barcode_data))
        )


class ELBTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="elb_instances")
    pnr = models.CharField(max_length=6, verbose_name="PNR")
    sequence_number = models.PositiveSmallIntegerField(verbose_name="Sequence number")
    barcode_data = models.BinaryField()

    class Meta:
        unique_together = [
            ["pnr", "sequence_number"],
        ]
        verbose_name = "ELB ticket"

    def __str__(self):
        return f"{self.pnr} - {self.sequence_number}"

    def as_ticket(self) -> t.ELBTicket:
        return t.ELBTicket(
            raw_ticket=bytes(self.barcode_data),
            data=elb.ELBTicket.parse(bytes(self.barcode_data)),
        )


class SSBTicketInstance(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="ssb_instances")
    distributor_rics = models.PositiveIntegerField(validators=[validators.MaxValueValidator(9999)], verbose_name="Distributor RICS")
    pnr = models.CharField(max_length=32, verbose_name="PNR", blank=True, null=True, unique=True)
    barcode_data = models.BinaryField()

    class Meta:
        verbose_name = "SSB ticket"

    def __str__(self):
        return str(self.pnr)

    def as_ticket(self) -> t.SSBTicket:
        envelope = ssb.Envelope.parse(bytes(self.barcode_data))

        if envelope.ticket_type == 2:
            data = ssb.NonReservationTicket.parse(envelope.data)
        elif envelope.ticket_type == 4:
            data = ssb.Pass.parse(envelope.data)
        elif envelope.issuer_rics == 1184 and envelope.ticket_type == 21:
            data = ssb.ns_keycard.Keycard.parse(envelope.data)
        else:
            raise NotImplementedError()

        return t.SSBTicket(
            raw_ticket=bytes(self.barcode_data),
            envelope=envelope,
            data=data
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
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="apple_registrations")
    device = models.ForeignKey(AppleDevice, on_delete=models.CASCADE, related_name="registrations")
    ticket_part = models.CharField(max_length=255, verbose_name="Ticket part", blank=True, null=True)

    class Meta:
        unique_together = [
            ["ticket", "device", "ticket_part"],
        ]


class DBSubscription(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="subscriptions")
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
