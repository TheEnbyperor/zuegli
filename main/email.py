from django.core import mail
from django.template.loader import render_to_string
from django.conf import settings
from . import models, gwallet
from .views import passes

def send_new_ticket_email(ticket: "models.Ticket"):
    if not ticket.account:
        return

    context = {
        "user": ticket.account.user,
        "ticket": ticket,
        "google_wallet_link": gwallet.create_jwt_link(ticket),
    }
    html_message = render_to_string("email/new_ticket.html", context)
    txt_message = render_to_string("email/new_ticket.txt", context)

    msg = mail.EmailMultiAlternatives(
        to=[ticket.account.user.email],
        subject=f"Your train ticket #{ticket.public_id()}",
        body=txt_message,
        from_email=settings.DEFAULT_FROM_EMAIL
    )
    msg.attach_alternative(html_message, "text/html")

    _, files = passes.make_pkpass_file(ticket)
    for file_name, file_contents in files:
        msg.attach(file_name, file_contents, "application/vnd.apple.pkpass")

    msg.send()
