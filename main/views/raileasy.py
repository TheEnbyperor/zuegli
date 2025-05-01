import niquests
import datetime
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import forms, raileasy, models


@login_required
def raileasy_login(request):
    if request.method == "POST":
        form = forms.RaileasyLoginForm(request.POST)
        if form.is_valid():
            r = niquests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword", params={
                "key": settings.RAILEASY_API_KEY,
            }, json={
                "email": form.cleaned_data["email"],
                "password": form.cleaned_data["password"],
                "returnSecureToken": True
            }, headers={
                "User-Agent": "Zuegli (q@magicalcodewit.ch)"
            })
            if not r.ok:
                messages.error(request, "Login failed")
            else:
                auth_data = r.json()
                messages.success(request, "Login successful")
                models.AccountOAuth.objects.update_or_create(
                    account=request.user.account,
                    provider="raileasy",
                    defaults={
                        "token": auth_data["idToken"],
                        "token_expires_at": timezone.now() + datetime.timedelta(seconds=int(auth_data["expiresIn"])),
                        "refresh_token": auth_data["refreshToken"],
                    }
                )
                raileasy.update_tickets(request.user.account)
                return redirect("account")
    else:
        form = forms.RaileasyLoginForm()

    return render(request, "main/account/raileasy_login.html", {
        "form": form,
    })
