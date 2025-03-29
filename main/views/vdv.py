from django.shortcuts import get_object_or_404, render
from .. import models


def view_smartcard(request, pk):
    smartcard_obj = get_object_or_404(models.VDVSmartcard, id=pk)

    return render(request, "main/vdv_smartcard.html", {
        "smartcard": smartcard_obj,
    })