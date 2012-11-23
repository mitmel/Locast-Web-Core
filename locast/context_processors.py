from django.conf import settings
from django.contrib.sites.models import get_current_site

def settings_variables(request):
    '''
    Allows settings to define which variables
    it wants to expose to templates
    '''

    d = {}

    if getattr(settings, 'CONTEXT_VARIABLES', None):
        for var in settings.CONTEXT_VARIABLES:
            if hasattr(settings, var):
                d[var] = getattr(settings, var)

    return d

def site_name(request):
    '''
    Gets the name of the site as defined in the site model
    '''

    site = get_current_site(request)
    return {'SITE_NAME': site.name}
