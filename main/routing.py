from django.urls import path

from .vdv_nm import nfc

websocket_urlpatterns = [
    path(r"ws/vdv-nfc", nfc.VDVConsumer.as_asgi()),
    path(r"ws/vdv-nfc-sam", nfc.VDVConsumer.as_asgi()),
]