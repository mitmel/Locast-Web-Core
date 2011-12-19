from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from locast import get_model

def get_user_model():
    ''' Gets the custom user model as defined by a specific locast app '''

    model_name = settings.USER_MODEL.split('.',2)[1].lower()
    model = get_model(model_name)
    if not model:
        raise ImproperlyConfigured('Custom User Model incorrectly defined')

    return model
