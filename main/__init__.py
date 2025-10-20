import urllib3.util
import niquests.adapters
from django.conf import settings

if settings.HTTP_PROXY_URL:
    socks_proxies = {
        'http': 'socks5h://cf-warp:1080',
        'https': 'socks5h://cf-warp:1080',
    }
else:
    socks_proxies = {}

retry_strategy = urllib3.util.Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = niquests.adapters.HTTPAdapter(max_retries=retry_strategy)
session = niquests.Session()
session.proxies.update(socks_proxies)
session.mount("http://", adapter)
session.mount("https://", adapter)