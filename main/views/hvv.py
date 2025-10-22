from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.conf import settings
from .. import forms, models, hvv, session
import datetime
import jwt


@login_required
def hvv_login(request):
    if request.method == "POST":
        form = forms.EOSLoginForm(request.POST)
        if form.is_valid():
            r = session.get("https://api.hochbahn.cloud/auth/token", auth=(
                f"{settings.HVV_APPLICATION_KEY}/{form.cleaned_data["username"]}", form.cleaned_data["password"]
            ), headers={
                "User-Agent": "Zuegli (q@magicalcodewit.ch)",
            })
            if r.status_code != 200:
                messages.error(request, "Login failed")
            else:
                messages.success(request, "Login successful")
                access_token = r.headers["authorization"][len("Bearer "):]
                device_id = r.headers["x-beam-client-id"]
                refresh_token = r.headers["x-beam-refresh-token"]

                auth_data = jwt.decode(access_token, options={"verify_signature": False})
                expiry = datetime.datetime.fromtimestamp(auth_data["exp"])

                models.AccountOAuth.objects.update_or_create(
                    account=request.user.account,
                    provider="hvv",
                    defaults={
                        "token": access_token,
                        "token_expires_at": expiry,
                        "refresh_token": refresh_token,
                        "device_id": device_id,
                    }
                )
                hvv.update_hvv_tickets.apply_async(args=(request.user.account.id,), queue="celery")
                return redirect("account")
    else:
        form = forms.EOSLoginForm()

    return render(request, "main/account/hvv_login.html", {
        "form": form,
    })
