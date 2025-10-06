from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .. import forms, eos, mvv, models

@login_required
def mvv_login(request):
    if request.method == "POST":
        form = forms.EOSLoginForm(request.POST)
        if form.is_valid():
            if not eos.login(request.user.account, "mvv", form.cleaned_data["username"], form.cleaned_data["password"]):
                messages.error(request, "Login failed")
            else:
                messages.success(request, "Login successful")
                mvv.update_mvv_tickets.apply_async(args=(request.user.account.id,), queue="celery")
                return redirect("mvv_account")
    else:
        form = forms.EOSLoginForm()

    return render(request, "main/account/mvv_login.html", {
        "form": form,
    })

@login_required
def mvv_account(request):
    if not request.user.account.is_mvv_authenticated():
        return redirect("mvv_login")

    account_oauth = models.AccountOAuth.objects.get(account=request.user.account, provider="mvv")
    fields = eos.get_customer_account(request.user.account, "mvv")

    return render(request, "main/account/mvv.html", {
        "fields": fields,
        "tickets": account_oauth.tickets,
    })