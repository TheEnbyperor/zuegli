from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def vestische_login(request):
    return render(request, "main/account/vestische_login.html")


@login_required
def nrway_login(request):
    return render(request, "main/account/nrway_login.html")