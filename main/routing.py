from django.urls import path

from .vdv_nm import nfc as vdv_nfc
from .uic import nfc as uic_nfc

websocket_urlpatterns = [
    path(r"ws/vdv-nfc", vdv_nfc.VDVConsumer.as_asgi()),
    path(r"ws/vdv-nfc-sam", vdv_nfc.VDVConsumer.as_asgi()),
    path(r"ws/uic-ndef-nfc", uic_nfc.Consumer.as_asgi()),
]