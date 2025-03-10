from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path(r"ws/vdv-nfc", consumers.VDVConsumer.as_asgi()),
]