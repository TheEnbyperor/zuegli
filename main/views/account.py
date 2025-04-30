from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, reverse, redirect
from .. import forms

@login_required
def index(request):
    calendar_url = reverse("account_calendar", args=(request.user.account.calendar_token,))

    return render(request, "main/account/index.html", {
        "user": request.user,
        "tickets": request.user.account.tickets.order_by("-last_updated"),
        "calendar_url": f"{settings.EXTERNAL_URL_BASE}{calendar_url}"
    })


@login_required
def edit(request):
    initial = {
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
    }
    if request.method == "POST":
        form = forms.AccountEditForm(request.POST, initial=initial)

        if form.is_valid():
            request.user.first_name = form.cleaned_data["first_name"]
            request.user.last_name = form.cleaned_data["last_name"]
            request.user.save()
            return redirect('account')
    else:
        form = forms.AccountEditForm(initial=initial)

    return render(request, "main/account/edit.html", {
        "form": form,
    })

