import hashlib
import string

from django.contrib.auth import get_user_model
from django.db import models

from locast.util import random_string

class UserConfirmationManager(models.Manager):

    '''Manager for the user confirmation model'''
    def create_confirmation(self, user, keymaker=None):
        '''
        Creates a new user confirmation entry into the model
            using submitted form

        user: user object submitted with request
        keymaker: key-generating function
        '''
        if keymaker == None:
            keymaker = self.default_keymaker

        # Create user confirmation with a generated key
        new_key = keymaker(user)
        uc = self.model(user=user, key=new_key)
        uc.save()

        return uc

    def get_user_by_key(self, key):
        '''
        Get the user from a key. Return None if invalid key
        '''

        user = None
        try:
            match = self.get(key=key)
            user = match.user
        except get_user_model().DoesNotExist:
            pass

        return user

    def default_keymaker(self, user):
        '''
        Default keymaker. Creates key based on random salt and email
        '''

        key = random_string(string.digits + string.ascii_letters, 10)
        key = key + user.email

        sha = hashlib.sha1()
        sha.update(key)
        key = sha.hexdigest()

        return key
