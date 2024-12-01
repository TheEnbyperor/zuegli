from django.contrib import admin
from django.shortcuts import redirect, get_object_or_404
from django.urls import path
from django.utils import timezone
from django.contrib import messages
from django.contrib.admin.utils import unquote
from . import models, apn


class VDVTicketInstanceInline(admin.StackedInline):
    extra = 0
    model = models.VDVTicketInstance


class UICTicketInstanceInline(admin.StackedInline):
    extra = 0
    model = models.UICTicketInstance


class RSPTicketInstanceInline(admin.StackedInline):
    extra = 0
    model = models.RSPTicketInstance


class ELBTicketInstanceInline(admin.StackedInline):
    extra = 0
    model = models.ELBTicketInstance


class SSBTicketInstanceInline(admin.StackedInline):
    extra = 0
    model = models.SSBTicketInstance


class AppleRegistrationInline(admin.StackedInline):
    extra = 0
    model = models.AppleRegistration
    readonly_fields = [
        "device",
        "ticket",
    ]


class TicketAccountInline(admin.StackedInline):
    extra = 0
    model = models.Ticket
    fk_name = "account"
    readonly_fields = [
        "pkpass_authentication_token",
        "last_updated",
    ]


class TicketDBSubscriptionInline(admin.StackedInline):
    extra = 0
    model = models.Ticket
    fk_name = "db_subscription"
    readonly_fields = [
        "pkpass_authentication_token",
        "last_updated",
    ]


class DBSubscriptionInline(admin.StackedInline):
    extra = 0
    model = models.DBSubscription
    readonly_fields = [
        "device_token"
    ]


@admin.register(models.Ticket)
class TicketAdmin(admin.ModelAdmin):
    readonly_fields = [
        "id",
        "pkpass_authentication_token",
        "last_updated",
    ]
    inlines = [
        VDVTicketInstanceInline,
        UICTicketInstanceInline,
        RSPTicketInstanceInline,
        ELBTicketInstanceInline,
        SSBTicketInstanceInline,
        AppleRegistrationInline,
    ]
    view_on_site = True
    list_display = [
        "id",
        "ticket_type",
        "last_updated"
    ]
    date_hierarchy = "last_updated"
    list_filter = [
        "ticket_type",
    ]
    search_fields = ["id"]
    change_form_template = "main/admin/ticket_change.html"

    def get_urls(self):
        urls = super().get_urls()
        urls = [
           path("force_update/<ticket_id>/",
                self.admin_site.admin_view(self.force_update),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_force_update"),
        ] + urls
        return urls

    def force_update(self, request, ticket_id):
        ticket = self.get_object(request, unquote(ticket_id))

        ticket.last_updated = timezone.now()
        ticket.save()
        apn.notify_ticket(ticket)

        messages.add_message(request, messages.INFO, "Update APN sent")

        return redirect(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change",
            ticket.id
        )


@admin.register(models.AppleDevice)
class AppleDeviceAdmin(admin.ModelAdmin):
    readonly_fields = [
        "device_id",
        "push_token",
    ]
    inlines = [
        AppleRegistrationInline,
    ]


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    readonly_fields = [
        "user",
        "db_token",
        "db_token_expires_at",
        "db_refresh_token",
        "db_refresh_token_expires_at",
        "saarvv_token",
        "saarvv_device_id",
    ]
    inlines = [
        TicketAccountInline,
        DBSubscriptionInline,
    ]


@admin.register(models.DBSubscription)
class DBSubscriptionAdmin(admin.ModelAdmin):
    readonly_fields = [
        "device_token"
    ]
    inlines = [
        TicketDBSubscriptionInline
    ]