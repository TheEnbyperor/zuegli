from django.conf import settings

def git_hash_context(request):
    return {
        "git_hash": settings.GIT_HASH,
    }