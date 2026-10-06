from django.conf import settings


def site_branding(request):
    """Makes these values available in EVERY template,
    e.g. {{ SITE_TITLE }} or {{ SITE_AUTHOR }}."""
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_TITLE': settings.SITE_TITLE,
        'SITE_AUTHOR': settings.SITE_AUTHOR,
        'SITE_AUTHOR_EMAIL': settings.SITE_AUTHOR_EMAIL,
    }