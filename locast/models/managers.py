import settings
import string

from django import dispatch
from django.contrib.auth.models import BaseUserManager
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models.manager import GeoManager
from django.db import models

from locast import get_model
from locast.auth.exceptions import PairingException
from locast.util import random_string

### User Management ###

class LocastUserManager(BaseUserManager):
    '''Custom manager for a User.'''

    def get_by_username(self, username):
        try:
            return self.get(username=username)
        except self.model.DoesNotExist:
            return None


class PairableUserManager(models.Manager): 

    # Settings for the generation of the auth_key
    auth_chars = string.digits
    auth_length = 7
    auth_key_chars = string.letters + string.digits
    auth_key_length = 24

    def _gen_unique_auth_secret(self):
        '''
        Generate a globally-unique authentication secret
        
        This ensures that this auth_secret is unique, so it can be used later
        on to locate the UID during a pairing.
        '''

        #another good technique for this is to create a hash of  
        #'sitesecret:uid'
        sec = random_string(self.auth_chars, self.auth_length)
        while self.filter(auth_secret=sec):
            sec = self.random_string(self.auth_chars, self.auth_length)
        return sec


    def pair_phone(self, auth_secret):
        '''
        Pairs a user's phone to the database
        
        Will update the user's auth_secret with a randomly-generated string
        that should be sent by the client on each following request.  If
        successful, will mark the user's paired flag.

        Returns the newly paired user.

        raises PairingException
        '''

        try:
            u = self.get_by_auth_secret(auth_secret)
            if u.paired:
                raise PairingException('User has already paired')
            u.auth_secret = random_string(self.auth_key_chars, self.auth_key_length)
            u.paired = True
            u.save()
            return u
        except self.model.DoesNotExist, e:
            raise PairingException('User not found for given auth_secret')
        except self.model.MultipleObjectsReturned, e:
            raise PairingException('Multiple users for auth_secret found.')
        except e:
            raise PairingException('Uncaught Error: %s' % e)       

    def get_by_auth_secret(self, auth_secret):
        ''' Finds a user given the globally-unique auth secret. '''

        return self.get(auth_secret=auth_secret)

### Other managers ###

class CommentManager(models.Manager):

    def get_comments(self, obj):
        ''' Returns all comments made about a specific object. '''
        ctype = ContentType.objects.get_for_model(obj)
        return self.filter(content_type__pk=ctype.id, object_id=obj.id).order_by('-created')


class BoundryManager(GeoManager):
    
    def get_default_boundry(self):
        defs = self.filter(default = True)
        if len(defs):
            return defs[0]

        return None


class UUIDManager(models.Manager):

    def get_by_uuid(self, uuid):
        return self.model.objects.get(uuid=uuid)


class RouteManager(models.Manager):
    ''' Manager for Route model '''

    def get_routes_by_feature(self, feature):
        routes = []
        ct = ContentType.objects.get_for_model(feature)
        pfs = self.filter(content_type = ct,
            object_id = feature.id)

        for pf in pfs:
            routes.append(pf.route)

        return routes


user_activity_signal = dispatch.Signal(providing_args=['action'])

class UserActivityManager(models.Manager):
    ''' Manager for the UserActivity model. '''

    def create_activity(self, user, object, action):
        ''' 
        Creates a new User Activity object 

        Arguments:

            user
                User object who initiated the action

            object
                The object that was acted upon

            action
                The action as a string. Must be defined in 
                settings.USER_ACTIONS
        '''

        if settings.USER_ACTIONS and not action in settings.USER_ACTIONS:
            raise Exception('Invalid Action')

        if user.is_authenticated():
            ua = get_model('useractivity')()
            ua.user = user
            ua.action = action
            ua.content_object = object
            ua.save()
            user_activity_signal.send(sender=ua, action=ua.action)

    def get_activities_by_model(self, model):
        ''' Returns all activities relating to a certain model. '''

        ct = ContentType.objects.get_for_model(model)
        return self.filter(content_type=ct)

    def get_activities_by_user(self, user):
        ''' Returns all activities initiated by a certain user. '''

        return self.filter(user=user)

    def get_activities(self, obj):
        ''' Returns activities relating to a specific object. '''

        ctype = ContentType.objects.get_for_model(obj)
        return self.filter(content_type__pk=ctype.id, object_id=obj.id)
