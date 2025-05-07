import django.contrib.auth
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, reverse, redirect
from django.utils.translation import gettext_lazy as _
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


@login_required
def set_password(request):
    if request.method == "POST":
        form = forms.SetPasswordForm(request.user, request.POST)

        if form.is_valid():
            request.user.set_password(form.cleaned_data["new_password1"])
            messages.info(request, _("Your password has been updated"))
            return redirect("account")
    else:
        form = forms.SetPasswordForm(request.user)

    return render(request, "main/account/set_password.html", {
        "form": form,
    })


def login(request):
    if request.user.is_authenticated:
        return redirect("account")

    if request.method == "POST":
        login_form = forms.LoginForm(request.POST)

        if login_form.is_valid():
            if user := django.contrib.auth.authenticate(
                request,
                username=login_form.cleaned_data["username"],
                password=login_form.cleaned_data["password"]
            ):
                django.contrib.auth.login(request, user)
                if "next" in request.GET:
                    return redirect(request.GET["next"])
                else:
                    return redirect("index")
            else:
                messages.error(request, _("Invalid username or password"))
    else:
        login_form = forms.LoginForm()

    return render(request, "registration/login.html", {
        "login_form": login_form,
    })