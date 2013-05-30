import settings
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes import generic
from django.contrib.gis.db import models as gismodels
from django.contrib.gis.geos import Point
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from locast import get_model
from locast.api import datetostr, api_serialize


class Syncable(models.Model):
    ''' 
    Interface to be used for a model that will be synced with a client via the API
    '''

    class Meta:
        abstract = True

    uuid = models.CharField(max_length=36, unique=True, blank=True)
        
    created = models.DateTimeField('date created', default = timezone.now, editable = False)

    modified = models.DateTimeField('date modified', default = timezone.now, editable = False)

    def _api_serialize(self, request):
        d = {}

        d['created'] = datetostr(self.created)
        d['modified'] = datetostr(self.modified)
        d['uuid'] = self.uuid

        return d

    def _generate_uuid(self):
        return unicode(uuid.uuid4())

    def _pre_save(self):
        if not self.uuid:
            self.uuid = self._generate_uuid()


class Authorable(Syncable):
    ''' 
    Interface to be used for any model that is created by a user in the system.
    '''

    class Meta:
        abstract = True

    def _api_serialize(self, request):
        d = Syncable._api_serialize(self, request)

        author = api_serialize(self.author)
        d['author'] = author

        if request:
            d['is_author'] = self.is_author(request.user)
            d['allowed_edit'] = self.allowed_edit(request.user)

        return d

    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    def is_author(self, user):
        ''' Returns true if the user is the author '''

        return ( user == self.author ) 

    def allowed_access(self, user):
        ''' Authorable models can be accessed by anyone '''

        return True

    def allowed_edit(self, user):
        ''' Authorable models can be edited by anyone who is authenticated '''

        return user.is_authenticated()

    def _pre_save(self):
       Syncable._pre_save(self)
       self.modified = timezone.now()
    

class PrivatelyAuthorable(Authorable):
    ''' 
    Interface to be used for any model creatable by a user in the system,
    and with privacy considerations. 

    "public" allows for anyone to access or edit
    "protected" allows for anyone to access but only the author to 
    "private" allows only the author to access and edit.
    '''

    PRIVACY_PUBLIC = 1
    PRIVACY_PROTECTED = 2
    PRIVACY_PRIVATE = 3

    PRIVACY_CHOICES = (
        (PRIVACY_PUBLIC, _('Public')),
        (PRIVACY_PROTECTED, _('Protected')),
        (PRIVACY_PRIVATE, _('Private')),
    )

    DEFAULT_PRIVACY = PRIVACY_PUBLIC

    if hasattr(settings, 'DEFAULT_PRIVACY'):
        if settings.DEFAULT_PRIVACY:
            DEFAULT_PRIVACY = settings.DEFAULT_PRIVACY

    class Meta:
        abstract = True

    def _api_serialize(self, request):
        d = Authorable._api_serialize(self, request)

        if self.privacy:
            d['privacy'] = self.get_privacy_name(self.privacy)

        if request:
            d['allowed_edit'] = self.allowed_edit(request.user)

        return d

    def _pre_save(self):
        Authorable._pre_save(self)
        # Done this way to allow for auto forms to not specify privacy
        if not self.privacy:
            self.privacy = PrivatelyAuthorable.DEFAULT_PRIVACY

    privacy = models.PositiveSmallIntegerField(choices = PRIVACY_CHOICES, default = DEFAULT_PRIVACY, blank=True, null=True)

    @staticmethod
    def get_privacy_name(value):
        ''' Get the name of the privacy state correlating to the value given. '''

        privacy_dict = {}
        for choice in PrivatelyAuthorable.PRIVACY_CHOICES:
            privacy_dict[choice[0]] = choice[1].lower()

        try:
            return privacy_dict[value]
        except KeyError:
            raise ValueError('Invalid Privacy Value')
            
    @staticmethod
    def get_privacy_value(name):
        ''' Get the value of the privacy state correlating to the name given. '''

        privacy_dict = {}
        for choice in PrivatelyAuthorable.PRIVACY_CHOICES:
            privacy_dict[choice[0]] = choice[1].lower()

        name = name.lower()
        for k,v in privacy_dict.iteritems():
            if v==name: return k

        raise ValueError('Invalid Privacy Name')

    def allowed_access(self, user):
        ''' Returns true if the user is allowed to access the given object. '''

        if self.privacy == self.PRIVACY_PRIVATE:
            return ( self.is_author(user) | user.is_superuser )
        else:
            return True

    def allowed_edit(self, user):
        ''' Returns true if the user is allowed to edit the object. '''

        if self.privacy == self.PRIVACY_PROTECTED or self.privacy == self.PRIVACY_PRIVATE:
            return ( self.is_author(user) | user.is_superuser )
        else:
            return True

    def allowed_privacy_edit(self, user):
        ''' Returns true if the user is allowed to change the privacy. '''

        return ( self.is_author(user) | user.is_superuser )

    @staticmethod
    def get_privacy_q(request):
        '''
        Returns a Q object that can be used to filter objects based on the
        request.user
        '''

        if request.user.is_superuser:
            return Q()

        if request.user.is_authenticated():
            return (Q(privacy__lt=3) | Q(author=request.user))

        return Q(privacy__lt=3)


class Titled(models.Model):

    class Meta:
        abstract = True

    def _api_serialize(self, request):
        d = {}
        d['title'] = self.title
        if self.description:
            d['description'] = self.description

        return d

    title = models.CharField(max_length=160)

    description = models.TextField(blank=True, null=True)


class Locatable(models.Model):
    ''' Interface for any model that has a location (single point) '''

    class Meta:
        abstract = True

    def _api_serialize(self, request):
        d = {} 
        if self.location:
            d['location'] = [self.location.x, self.location.y]

        return d
        
    location = gismodels.PointField(null=True,blank=True,srid=4326)

    def set_location(self, lon, lat):
        ''' Sets the location using the given lon and lat. '''

        self.location = Point(lon, lat)


class Flaggable(models.Model):
    '''
    Interface for any model that can be flagged as objectionable or 
    inappropriate by a user of the system. Generally used for user created
    content. 
    '''

    class Meta:
        abstract = True

    flags = generic.GenericRelation('Flag')

    def flag(self, user, reason=''):
        ''' Flag this object. '''

        if not user.is_authenticated():
            return None

        flag_model = get_model('flag')
        flag = None

        if not self.is_flagged_by(user):
            flag = flag_model(content_object=self, user=user, reason=reason)
            flag.save()

        return flag

    def is_flagged_by(self, user):
        ''' Checks to see if the given user has flagged this object. '''

        if not user.is_authenticated():
            return False

        flags = self.flags.filter(user=user)
        return (not (flags.count() == 0))


# Tied to modelbases.Comment
class Commentable(models.Model):
    ''' This class of item can be commented on. '''

    class Meta:
        abstract = True

    comments = generic.GenericRelation('Comment')

    def comment(self, user, body):
        comment_model = get_model('comment')
        c = comment_model()
        c.author = user
        c.body = body
        c.content_object = self
        c.save()
        return c


class Favoritable(models.Model):
    ''' Interface for a class that can be favorited by a user. '''

    class Meta:
        abstract = True

    def _api_serialize(self, request):
        d = {}
        if request:
            d['favorite'] = self.is_favorited_by(request.user)

        d['favorite_count'] = self.favorited_by.count()

        return d

    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_%(class)s', null=True, blank=True)

    def favorite(self, user): 
        ''' Favorite this object. '''

        self.favorited_by.add(user)

    def unfavorite(self, user): 
        ''' Unfavorite this object. '''

        self.favorited_by.remove(user)

    def is_favorited_by(self, user):
        ''' Checks to see if the user has favorited this object '''

        if not user.is_authenticated():
            return False

        favorites = self.favorited_by.filter(username=user.username)
        return (not (favorites.count() == 0))


# Tied to modelbases.Tag
class Taggable(models.Model):
    '''
    Interface for any model that can be tagged using a semantic tag
    ( 32 characters )
    '''

    class Meta:
        abstract = True

    def _api_serialize(self, request):
       d = {}
       d['tags'] = map(lambda t: t.name, self.tags.filter(system_tag=False))
       d['system_tags'] = map(lambda t: t.name, self.tags.filter(system_tag=True))
       return d

    tags = models.ManyToManyField('tag', related_name='tag_%(class)s', null=True, blank=True)

    # Sets all non-system tags based on a list of tags (string or python list)
    def set_tags(self, tags):
        '''
        Sets the tags from either a list of tags or a simple comma-separated
        list of tags. Does not correctly handle quoted or escaped commas.
        '''

        # If it's a string, make it into a list of tag names
        if isinstance(tags, str) or isinstance(tags, unicode):
            tags = Taggable.tag_string_to_list(tags)

        # Clear all non-system tags
        for t in self.tags.filter(system_tag=False):
            self.tags.remove(t)

        # Add all the tags.
        for tagname in tags:
            self.add_tag_by_name(tagname)

    def add_tag_by_name(self, tagname, system_tag=False):
        # TODO: better length checking. exception perhaps?
        if len(tagname) <= 32:
            tag_model = get_model('tag')
            tag, created = tag_model.objects.get_or_create(name=tagname)
            if created and system_tag:
                tag.system_tag = True
                tag.save()

            self.tags.add(tag)

    def get_tag_by_name(self, tagname):
        tag = None
        try:
            tag = self.tags.get(name=tagname)
        except get_model('tag').DoesNotExist:
            pass

        return tag

    def remove_tag_by_name(self, tagname):
        tag = self.get_tag_by_name(tagname)
        if tag:
            self.tags.remove(tag)

    @property
    def visible_tags(self): return self.tags.filter(system_tag=False)

    @property
    def system_tags(self): return self.tags.filter(system_tag=True)

    @staticmethod
    def tag_string_to_list(csv):
        ''' Parses a string of tags and returns a set of tag names. '''
        tag_model = get_model('tag')
        tags = set(map(lambda rawtag: tag_model.filter_tag(rawtag), csv.split(',')))
        if '' in tags:
            tags.remove('')
        return tags


class Joinable(models.Model):
    ''' This class of item can be joined. '''

    class Meta:
        abstract = True

    member = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="member_%(class)s", null=True, blank=True)

    def is_member(self, user):
        try:
            self.member.get(id=user.id)
        except get_user_model().DoesNotExist:
            return False

        return True

    def add_member(self, user):
        if not self.is_member(user):
            self.member.add(user)


#TODO
class Versionable(models.Model):
    ''' This class of item can be revisioned. '''

    class Meta:
        abstract = True


#### USER INTERFACES ####

class PairableUser(models.Model):
    '''
    An interface that allows for pairing-related information
    '''

    class Meta:
        abstract = True

    auth_secret = models.CharField(max_length=255,blank=True,null=True)
    paired = models.BooleanField(default=False)
    phone_uuid = models.CharField(max_length=255,blank=True,null=True)

    def _pre_save(self, *args, **kargs):
        ''' Force all users to have at least the initial 7-digit auth_secret. '''

        if not self.auth_secret:
            self.auth_secret = get_user_model().objects._gen_unique_auth_secret()
