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


class AppleRegistrationInline(admin.StackedInline):
    extra = 0
    model = models.AppleRegistration
    readonly_fields = [
        "device",
        "ticket",
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
        AppleRegistrationInline,
    ]
    view_on_site = True
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