import urllib3.util
import niquests.adapters
from django.conf import settings

if settings.HTTP_PROXY_URL:
    socks_proxies = {
        'http': settings.HTTP_PROXY_URL,
        'https': settings.HTTP_PROXY_URL,
    }
else:
    socks_proxies = {}

retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
session = niquests.Session(happy_eyeballs=True)
session.mount("http://", adapter)
session.mount("https://", adapter)