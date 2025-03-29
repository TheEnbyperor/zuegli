from django.shortcuts import render


def nfc_index(request):
    return render(request, 'main/nfc_index.html')