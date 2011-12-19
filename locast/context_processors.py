from django.conf import settings

def settings_variables(request):
    ''' Provides base URLs for use in templates '''

    d = {
        'HOST': settings.HOST,
        'BASE_URL': settings.BASE_URL,
        'FULL_BASE_URL': settings.FULL_BASE_URL,
        'MEDIA_URL': settings.MEDIA_URL
    }

    # Allows settings to define which variables
    # it wants to expose to templates

    if settings.CONTEXT_VARIABLES:
        for var in settings.CONTEXT_VARIABLES:
            if hasattr(settings, var):
                d[var] = getattr(settings, var)

    return d
