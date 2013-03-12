from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re

from django.contrib.auth import get_user_model

class BasicBackend(ModelBackend):

    def get_user(self, user_id):
        '''
        Get a user.
        '''

        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None


class LocastUsernameBackend(BasicBackend):
    ''' Authenticate using username '''

    def authenticate(self, username=None, password=None):
        '''
        Locast authenticate that returns the custom user model as defined in 
        settings. See locast.auth.get_user_model
        '''

        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username)
            if user.check_password(password):
                return user
        except user_model.DoesNotExist:
            return None


class LocastEmailBackend(BasicBackend):
    ''' Authenticate using email '''

    def authenticate(self, username=None, password=None):

        user_model = get_user_model()
        if email_re.search(username):
            try:
                user = user_model.objects.get(email=username)
            except user_model.DoesNotExist:
                return None

            if user.check_password(password):
                return user

        return None


class PairedMobileBackend(BasicBackend):
    ''' Backend that handles http api requests from a mobile which has been paired '''

    def authenticate(self, username=None, password=None):
        user_model = get_user_model()

        try:
            user = user_model.objects.get(username=username)
            if user.auth_secret == password:
                return user
        except user_model.DoesNotExist:
            return None

