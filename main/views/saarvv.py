from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import forms, eos, saarvv, models

@login_required
def saarvv_login(request):
    if request.method == "POST":
        form = forms.EOSLoginForm(request.POST)
        if form.is_valid():
            if not eos.login(request.user.account, "saarvv", form.cleaned_data["username"], form.cleaned_data["password"]):
                messages.error(request, "Login failed")
            else:
                messages.success(request, "Login successful")
                saarvv.update_saarvv_tickets.apply_async(args=(request.user.account.id,), queue="celery", expires=14400)
                return redirect("saarvv_account")
    else:
        form = forms.EOSLoginForm()

    return render(request, "main/account/saarvv_login.html", {
        "form": form,
    })

@login_required
def saarvv_account(request):
    if not request.user.account.is_saarvv_authenticated():
        return redirect("saarvv_login")

    account_oauth = models.AccountOAuth.objects.get(account=request.user.account, provider="saarvv")
    fields = eos.get_customer_account(request.user.account, "saarvv")

    return render(request, "main/account/saarvv.html", {
        "fields": fields,
        "tickets": account_oauth.tickets,
    })