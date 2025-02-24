import uuid

from django import template
from django.conf import settings
from django.utils import timezone
import datetime
import jwt

register = template.Library()

@register.simple_tag(name="mapkit_token")
def mapkit_token():
    if not settings.MAPKIT_KEY:
        return ""

    now = timezone.now()
    return jwt.encode({
        "iss": settings.PKPASS_CONF["team_id"],
        "iat": int((now - datetime.timedelta(minutes=5)).timestamp()),
        "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
        "origin": settings.ALLOWED_HOSTS[0]
    }, settings.MAPKIT_KEY, algorithm="ES256", headers={
        "kid": settings.MAPKIT_KEY_ID
    })

@register.simple_tag(name="mapkit_id")
def mapkit_id():
    return str(uuid.uuid4())
