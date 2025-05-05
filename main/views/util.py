import json
from django.templatetags.static import static
from django.core.files.storage import storages
from django.http import HttpResponse


def robots(request):
    with storages["staticfiles"].open("main/robots.txt") as f:
        return HttpResponse(f.read(), content_type="text/plain")


def apple_app_site_association(request):
    with storages["staticfiles"].open("main/apple-app-site-association.json") as f:
        return HttpResponse(f.read(), content_type="application/json")


def manifest(request):
    return HttpResponse(json.dumps({
        "id": "zuegli",
        "name": "Zügli",
        "icons": [{
            "src": static("main/icon.png"),
            "type": "image/png",
            "sizes": "512x512"
        }, {
            "src": static("main/icon.png"),
            "type": "image/png",
            "sizes": "512x512",
            "purpose": "maskable"
        }, {
            "src": static("main/icon-sm.png"),
            "type": "image/png",
            "sizes": "192x192"
        }, {
            "src": static("main/icon-sm.png"),
            "type": "image/png",
            "sizes": "192x192",
            "purpose": "maskable"
        }],
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#c42126",
        "background_color": "#c42126",
        "share_target": {
            "action": "/api/share_target/",
            "method": "POST",
            "enctype": "multipart/form-data",
            "params": {
                "files": [{
                    "name": "barcode",
                    "accept": ["image/*"]
                }, {
                    "name": "pdf",
                    "accept": ["application/pdf"]
                }]
            }
        }
    }), content_type="application/manifest+json")
