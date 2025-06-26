import base64
from django.contrib.auth.decorators import login_required
from django.http import Http404
from .. import oauth

SCHEMES = {
    "dbnav": "db",
    "bahnbonus": "bahnbonus",
    "de.eosuptrade.avvshop": "avv",
    "vestische": "vestische",
    "bvr": "nrway",
    "sobus": "sobus",
    "classic": "vrr",
    "bogestra": "bogestra",
    "dsw21": "dsw21",
    "dvg": "dvg",
    "hst": "hagen",
    "hcr": "hcr",
    "moebus": "moebus",
    "viersen": "viersen",
    "niag": "niag",
    "evag": "ruhrbahn-essen",
    "mvg": "ruhrbahn-muellheim",
    "sdg": "dormagen",
    "swn": "neuss",
    "swr": "remscheid",
    "stoag": "oberhausen",
    "swk": "swk",
    "ver": "ver",
}

@login_required
def oauth_login_start(request, provider: str):
    if provider not in oauth.PROVIDERS:
        raise Http404()

    return oauth.login_start(request, provider)

@login_required
def oauth_logout(request, provider: str):
    return oauth.logout(request, provider)

@login_required
def oauth_login_callback(request):
    if "url" not in request.GET:
        raise Http404()
    try:
        url = base64.urlsafe_b64decode(request.GET["url"]).decode("utf-8")
    except ValueError:
        raise Http404()

    scheme = url.split("://", 1)[0]

    if scheme not in SCHEMES:
        raise Http404()

    return oauth.login_callback(request, SCHEMES[scheme], url)
