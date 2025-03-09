from django.core.files.storage import storages
from django.http import HttpResponse


def robots(request):
    with storages["staticfiles"].open("main/robots.txt") as f:
        return HttpResponse(f.read(), content_type="text/plain")


def apple_app_site_association(request):
    with storages["staticfiles"].open("main/apple-app-site-association.json") as f:
        return HttpResponse(f.read(), content_type="application/json")