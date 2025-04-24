import secrets
import niquests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, reverse
from . import db

@login_required
def index(request):
    calendar_url = reverse("account_calendar", args=(request.user.account.calendar_token,))

    return render(request, "main/account/index.html", {
        "user": request.user,
        "tickets": request.user.account.tickets.order_by("-last_updated"),
        "calendar_url": f"{settings.EXTERNAL_URL_BASE}{calendar_url}"
    })

