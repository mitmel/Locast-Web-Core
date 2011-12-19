from django.conf import settings
from django.db.models import get_model as django_get_model

#TODO refactor this to somewhere it makes sense (models?)
def get_model(model):
    ''' Returns a model specific to this App '''

    return django_get_model(settings.APP_LABEL, model)

