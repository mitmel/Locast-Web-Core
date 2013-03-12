import commands
import mimetypes
import os
import uuid

from datetime import datetime, time

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models as gismodels
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from locast import get_model
from locast.api import api_serialize
from locast.models import ModelBase
from locast.models.interfaces import Authorable
from locast.models.managers import BoundryManager, CommentManager, LocastUserManager, RouteManager, UserActivityManager

help_text_automatic = _('Created automatically.')

class LocastContent(ModelBase):
    '''
    An abstract model that encompasses all media content types (audio, video, text, photo etc...)

    All app specific content models should inherit from this, and the model of the content type
    like the following example:

    class AppContent(LocastContent, interfaces...)
    class AppVideoContent(AppContent, VideoContent)
    '''

    class Meta:
        abstract = True

    class InvalidMimeType(Exception): pass

    # The type of content stored in the content property
    # based off of ContentType model field
    content_type_model = models.CharField(max_length=100)

    STATE_INCOMPLETE = 1
    STATE_COMPLETE = 2
    STATE_PROCESSING = 3
    STATE_FINISHED = 4

    STATE_CHOICES = (
        (STATE_INCOMPLETE, 'Incomplete'),
        (STATE_COMPLETE, 'Complete'),
        (STATE_PROCESSING, 'Processing'),
        (STATE_FINISHED, 'Finished'),
    )

    content_state = models.PositiveSmallIntegerField(choices=STATE_CHOICES, default = 1)

    mime_type = models.CharField(
            #TODO: 90 is arbitrary
            max_length=90,
            blank=True,
            null=True,
            help_text=help_text_automatic)

    @staticmethod
    def valid_mimetype(mime_type, mime_types):
        ''' Checks if a mime_type is valid based on a list of mime_types '''

        if mime_type in map(lambda m: m[0], mime_types):
            return True

        return False

    @staticmethod
    def path_to_mimetype(path, mime_types):
        ''' Converts a path to a mimetype, checking it against valid mime_types '''

        mime_type = mimetypes.guess_type(path)[0]

        if LocastContent.valid_mimetype(mime_type, mime_types):
            return mime_type

        return None

    @staticmethod
    def path_to_content_model(path, content_models):
        ''' Given a path and an array of content_models, returns the one that matches '''
        mime_type = mimetypes.guess_type(path)[0]
        for cm in content_models:
            if cm.valid_mimetype(mime_type, cm.MIME_TYPES):
                return cm

    @staticmethod
    def serialize_resource(url):
        d = {}
        d['url'] = url
        d['mime_type'] = mimetypes.guess_type(url)[0]
        return d

    def _api_serialize(self, request=None):
        ''' See: locast.api.api_serialize '''

        d = self.content.content_api_serialize()
        if hasattr(self.content, 'get_api_uri'):
            d['uri'] = self.content.get_api_uri()
        d['content_type'] = self.content_type_model
        d['id'] = self.id
        return d

    def _pre_save(self):
        # application
        content_class = self.__class__.__base__

        # Make sure this is being called from the content itself.
        if (not self.content_type_model) and (not self.content):
            self.content_type_model = ContentType.objects.get_for_model(self).model

        for interface in content_class.__bases__:
            # The first base of the custom content class will be LocastContent,
            # so this is to avoid infinite recursion
            if not interface == content_class.__base__:
                if hasattr(interface, '_pre_save'):
                    interface._pre_save(self)

        if hasattr(self, '_content_pre_save'):
            self._content_pre_save()

    def _post_save(self):
        content_class = self.__class__.__base__

        for interface in content_class.__bases__:
            if not interface == content_class.__base__:
                if hasattr(interface, '_post_save'):
                    interface._post_save(self)

    @property
    def content(self):
        ''' This is a pointer from the content model to the specific content type '''

        if hasattr(self, self.content_type_model):
            return getattr(self, self.content_type_model)
        return None

    @property
    def contentmodel(self):
        ''' This is a pointer from the specific content type back to the content model '''

        #TODO: makes this less of a hack...
        # it's currently based on the default naming of a parent in django
        # model inheritence.

        content_model_str = self.__class__.__base__.__name__.lower()
        content_model_attr = content_model_str + '_ptr'

        # If its locastcontent, then its being called from contentmodel
        if hasattr(self, content_model_attr) and not (content_model_str=='locastcontent') :
            return getattr(self, content_model_attr)
        return None


class TextContent(models.Model):
    ''' Simple text content model. Stores up to 1024 characters. '''

    class Meta:
        abstract = True

    def content_api_serialize(self, request=None):
        d = dict(text=self.text)
        return d


    text = models.TextField(blank=True,null=True)

# Take in a filename, return a unique filename that only keeps
# the extension

def _mostly_unique_filename(filename):
    filename, ext = os.path.splitext(filename)
    fn = ('%s' % uuid.uuid4()).split('-')
    return '%s%s%s' % (fn[-1], fn[-2], ext)

def get_content_file_path(instance, filename):
    filename = _mostly_unique_filename(filename)
    now = datetime.now()
    return os.path.join('content/%d/%d/%d/' % (now.year, now.month, now.day), filename)

def get_derivative_file_path(instance, filename):
    filename = _mostly_unique_filename(filename)
    now = datetime.now()
    return os.path.join('derivatives/%d/%d/%d/' % (now.year, now.month, now.day), filename)


class ImageContent(models.Model):

    class Meta:
        abstract = True

    MIME_TYPES = (
        # IANA format http://www.iana.org/assignments/media-types/
        ('image/gif', 'GIF'),
        ('image/jpeg', 'JPEG'),
        ('image/png', 'PNG'),
        ('image/tiff', 'TIFF'),
    )

    def content_api_serialize(self, request=None):
        d = {}
        if self.file:
            d['resources'] = {}
            d['resources']['primary'] = self.serialize_resource(self.file.url)

        return d

    def _content_pre_save(self):
        if self.file and not self.mime_type:
            self.mime_type = self.path_to_mimetype(self.file.path, self.MIME_TYPES)
            if not self.mime_type:
                raise self.InvalidMimeType

    file = models.FileField(
            upload_to=get_content_file_path,
            blank=True)

    def create_file_from_data(self, raw_data, mime_type):
        '''
        Takes in raw data and a mime_type and creates the file
        '''

        if not self.valid_mimetype(mime_type, self.MIME_TYPES):
            raise self.InvalidMimeType

        cf = ContentFile(raw_data)

        # See: http://bugs.python.org/issue4963.
        mimetypes.init()
        ext = mimetypes.guess_extension(mime_type)

        filename = _mostly_unique_filename('file_%s%s' % (self.id, ext))

        self.file.save(filename, cf)


class VideoContent(models.Model):
    ''' Content model for video content. '''

    class Meta:
        abstract = True

    MIME_TYPES = (
        # IANA format http://www.iana.org/assignments/media-types/
        ('video/mp4', 'MPEG4'),
        ('video/H264', 'H264'),
        ('video/3gpp', '3gpp'),
        ('video/3gpp2', '3gpp2'),
        ('video/quicktime', 'QuickTime'),
        ('video/mpeg', 'MPEG'),
    )

    def content_api_serialize(self, request=None):
        d = {}

        if self.file_exists(self.file):

            if self.duration:
                d['duration'] = unicode(self.duration)

            d['mime_type'] = self.mime_type

            resources = {}
            resources['primary'] = self.serialize_resource(self.file.url)

            if self.file_exists(self.screenshot):
                resources['screenshot'] = self.serialize_resource(self.screenshot.url)

            if self.file_exists(self.animated_preview):
                resources['preview'] = self.serlialize_resource(self.animated_preview.url)

            if self.file_exists(self.web_stream_file):
                resources['web_stream'] = self.serialize_resource(self.web_stream_file.url)

            d['resources'] = resources

        return d

    def _content_pre_save(self):
        if self.file and not self.mime_type:
            self.mime_type = self.path_to_mimetype(self.file.path, self.MIME_TYPES)
            if not self.mime_type:
                self.file = None
                raise self.InvalidMimeType

    #### Fields ####

    file = models.FileField(
            upload_to=get_content_file_path,
            blank=True)

    compressed_file = models.FileField(
            upload_to=get_derivative_file_path,
            blank=True,
            help_text=help_text_automatic)

    web_stream_file = models.FileField(
            upload_to=get_derivative_file_path,
            blank=True,
            help_text=help_text_automatic)

    screenshot = models.ImageField(
            upload_to=get_derivative_file_path,
            blank=True,
            help_text=help_text_automatic)

    animated_preview = models.FileField(
            upload_to=get_derivative_file_path,
            blank=True,
            help_text=help_text_automatic)

    duration = models.TimeField(null=True,blank=True, help_text=help_text_automatic)

    ### Instance Methods ###

    def file_exists(self, filefield):
        '''
        Checks if a file from a filefield exists
        '''

        #TODO: check the actual existence of the path using 
        # django.core.files.storage import default_storage
        if filefield and filefield.path:
            return True

        return False

    def is_file_current(self, filefield):
        '''
        Checks to see if a generated file (screenshot, web stream, compressed) is up
        to date by comparing it to the source. Returns false if the source
        file does not exist
        '''

        if self.file_exists(filefield):
            if os.path.getmtime(filefield.path) > os.path.getmtime(self.file.path):
                return True

        return False

    def get_filename(self, path):
        '''
        Takes a path, and returns a tuple of the filename and extension
        /path/filename.jpg would return ('filename', 'jpg')
        '''

        return os.path.split(path)[-1].split('.')

    # TODO: these file helper methods should perhaps be moved to an abstract
    # class, to be used with video content, photo content etc.

    def create_file_from_data(self, raw_data, mime_type):
        '''
        Takes in raw data and a mime_type and creates the file
        '''

        if not self.valid_mimetype(mime_type, self.MIME_TYPES):
            raise self.InvalidMimeType

        cf = ContentFile(raw_data)
        ext = mimetypes.guess_extension(mime_type)
        filename = 'mobile_upload_%s%s' % (self.id, ext)
        self.file.save(filename, cf)

    def generate_web_stream(self, force_update=False, verbose=False):
        ''' Create an web streamable version of our file, if necessary. '''

        # Make sure the file exists
        if not self.file_exists(self.file):
            if verbose: print 'Source file does not exist'
            return

        # If the web streamable file is current, don't do anything
        if not force_update and self.is_file_current(self.web_stream_file):
            return

        # Create a placeholder file
        if not self.file_exists(self.web_stream_file):
            web_stream_filename = self.get_filename(self.file.path)[0] + '.flv'
            self.web_stream_file.save(web_stream_filename, ContentFile(''), False)

        if verbose: print 'Making web streamable version to %s' % self.web_stream_file.path

        #generate web streamable version
        makeweb = 'lcvideo_mkflv %s %s' % (self.file.path, self.web_stream_file.path)
        webresult = commands.getoutput(makeweb)
        webresult = webresult.replace('Multiple frames in a packet from stream 1\n','')

        if verbose: print webresult + '\n\n'

        self.save()

    def generate_compressed(self, force_update=False, verbose=False):
        ''' Create a compressed version of our file, if necessary. '''

        # Make sure the file exists
        if not self.file_exists(self.file):
            if verbose: print 'Source file does not exist'
            return

        # If the compressed file is current, don't do anything
        if not force_update and self.is_file_current(self.compressed_file):
            return

        # Create a placeholder file
        if not self.file_exists(self.compressed_file):
            compressed_filename = self.get_filename(self.file.path)[0] + '_small.mp4'
            self.compressed_file.save(compressed_filename, ContentFile(''), False)

        if verbose: print 'Compressing non-3gp to %s' % self.compressed_file.path

        #generate compressed version
        makeCompressed = 'lcvideo_compress %s %s' % (self.file.path, self.compressed_file.path)
        compresult = commands.getoutput(makeCompressed)
        compresult = compresult.replace('Multiple frames in a packet from stream 1\n','')

    def generate_screenshot(self, force_update=False, verbose=False):
        ''' Generate a screenshot using the lcvideo_screenshot script '''

        # Make sure the file exists
        if not self.file_exists(self.file):
            if verbose: print 'Source file does not exist'
            return

        # If the screenshot is up to date, and we're not forcing, no need to do nothin
        if self.is_file_current(self.screenshot) and not force_update:
            if verbose: print 'Screenshot Exists'
            return

        if not self.file_exists(self.screenshot):
            screenshot_filename = self.get_filename(self.file.path)[0] + '.jpg'
            self.screenshot.save(screenshot_filename, ContentFile(''), False)

        if verbose: print 'Generating screenshot to %s' % self.screenshot.path

        # Create the screenshot using ffmpeg, 2 seconds into video
        make_screenshot = 'lcvideo_screenshot %s %s 00:00:02' % (self.file.path, self.screenshot.path)
        screenshot_result = commands.getoutput(make_screenshot)

        # If video was not long enough, just grab the first frame...
        if not os.path.getsize(self.screenshot.path):
            make_screenshot = 'lcvideo_screenshot %s %s' % (self.file.path, self.screenshot.path)
            screenshot_result = commands.getoutput(make_screenshot)

        # Use this opportunity to get the duration...
        # TODO: yuck fix this
        try:
            self.duration = time(*map(int, screenshot_result.partition('Duration: ')[2].partition('.')[0].split(':')))
        except:
            pass

        self.save()

    def generate_preview(self, force_update = False, verbose = False):
        '''
        Generate a preview version (animated gif) of the video using the
        lcvideo_preview script.
        '''

        # Make sure the file exists
        if not self.file_exists(self.file):
            if verbose: print 'Source file does not exist'
            return

        # If the preview is up to date, and we're not forcing, no need to do nothin
        if self.is_file_current(self.animated_preview) and not force_update:
            if verbose: print 'Animated Preview Exists'
            return

        # Create a placeholder file
        if not self.file_exists(self.animated_preview):
            preview_filename = self.get_filename(self.file.path)[0] + '.gif'
            self.animated_preview.save(preview_filename, ContentFile(''), False)

        make_preview = 'lcvideo_preview %s %s' % (self.file.path, self.animated_preview.path)
        preview_result = commands.getoutput(make_preview)

        self.save()

    def make_mobile_streamable(self):
        '''
        Uses qt-faststart to make the file itself able to be streamed
        on android devices.
        '''

        if not self.file_exists(self.file):
            return

        makestream = 'qt-faststart-inplace %s' % (self.file.path)
        makestream_result = commands.getoutput(makestream)


class LocastUser(ModelBase, AbstractUser):
    '''
    A wrapper model for Django user, adding some Locast specific fields,
    as well as a custom manager with pairing methods.
    '''

    class Meta:
        abstract = True

    # Override django default
    def get_absolute_url(self):
        return None

    def _api_serialize(self, request=None):
        d = {}
        if self.display_name:
            d['display_name'] = self.display_name

        return d

    display_name = models.CharField(max_length=32, null=True, blank=True)

    objects = LocastUserManager()

    # Language codes are in IETF format as described in RFC 4646 (http://tools.ietf.org/html/rfc4646)
    language = models.CharField(max_length=90, choices=settings.LANGUAGES,default='en')

    # Default display_name behavior. Override this if you'd like.
    def generate_display_name(self):
        if self.first_name and self.last_name:
            self.display_name = self.first_name + ' '  + self.last_name[0] + '.'

    def _pre_save(self):
        if not self.display_name:
            self.generate_display_name()


class UserActivity(ModelBase):
    '''
    Model used to log actions of users within the system. Don't create
    these manually, use the UserActivityManager.
    '''

    class Meta:
        abstract = True
        verbose_name = _('User activity')
        verbose_name_plural = _('User activities')

    def _api_serialize(self, request=None):
        return dict(
            user=self.user.username,
            time=unicode(self.time),
            action=self.action,
            object_type = ContentType.objects.get_for_model(self.content_object).model,
            object=api_serialize(self.content_object, request=None))

    objects = UserActivityManager()

    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    time = models.DateTimeField('activity time', default=timezone.now, editable=False)
    action = models.CharField(max_length=140, blank=True)

    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

## Interface related models ##

# TODO: make this threadable?
# Tied to interfaces.Commentable
class Comment(ModelBase, Authorable):
    '''
    A model used by the Commentable interface representing a single
    comment made by a user.
    '''

    class Meta:
        abstract = True
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __unicode__(self):
        return unicode(self.body) + ' (id: ' + unicode(self.id) + ')'

    def _api_serialize(self, request):
        d = Authorable._api_serialize(self, request)
        d['author'] = api_serialize(self.author)
        d['content'] = self.body

        return d

    objects = CommentManager()

    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    body = models.TextField()


# tied to intefaces.Taggable
class Tag(ModelBase):

    name = models.CharField(max_length=32, primary_key=True)

    # Is this a system tag
    system_tag = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __unicode__(self):
        return unicode(self.name)

    @staticmethod
    def filter_tag(raw_text):
        ''' Normalizes human-entered text into a tag name. '''

        t = raw_text.strip().lower()
        t = filter(lambda s: s.isalnum() or s.isspace(), t)
        return t


# tied to interfaces.Flaggable
class Flag(ModelBase):
    '''
    A flag, which is created to indicate inappropriate content.
    See interface: Flaggable.
    '''

    class Meta:
        abstract = True
        verbose_name = _('Flag')
        verbose_name_plural = _('Flags')

    def __unicode__(self):
        return unicode(self.content_type) + ': ' + unicode(self.content_object)

    object_id = models.PositiveIntegerField()

    content_type = models.ForeignKey(ContentType)

    content_object = generic.GenericForeignKey('content_type', 'object_id')

    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    reason = models.CharField(max_length=64)


class Boundry(ModelBase):

    class Meta:
        abstract = True
        verbose_name = _('boundry')
        verbose_name_plural = _('boundries')

    def __unicode__(self):
        return u'%s' % self.title

    objects = BoundryManager()

    title = models.CharField(max_length=160)

    bounds = gismodels.PolygonField()

    default = models.BooleanField(default=False)

    def _pre_save(self):
        if self.default:
            cur_defs = get_model('boundry').objects.filter(default=True)
            for c in cur_defs:
                c.default = False
                c.save()


class RouteFeature(ModelBase):
    ''' A generic model which relates a locatable model to a route. '''

    class Meta:
        abstract = True

    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.ForeignKey(ContentType, null=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    index = models.PositiveSmallIntegerField()

    route = models.ForeignKey('Route')

    def get_location(self):
        return self.content_object.location


class Route(ModelBase):
    '''
    A model which represents an ordered set of locatable content.

    note: only works with models inheriting from the locatable interface,
    or with any model that stores its location in a field named "location".
    '''

    class Meta:
        abstract = True

    def _api_serialize(self, request=None):
        coords = []
        for pf in self.routefeature_set.all():
            if pf.content_object.location:
                coords.append((pf.content_object.location.x,
                    pf.content_object.location.y))

        d = {}
        d['id'] = int(self.id)
        d['geometry'] = {
            'type':'LineString',
            'coordinates':coords
        }

        return d

    objects = RouteManager()

    def add_feature(self, object, index = None):
        ''' Add a feature. '''

        if not self.has_feature(object):
            pf = get_model('routefeature')(route = self)
            pf.content_object = object
            if not index:
                pf.index = (self.routefeature_set.count()+1)
            pf.save()


    def has_feature(self, object):
        ''' Check for the existence of an object within the route. '''

        ct = ContentType.objects.get_for_model(object)
        return self.routefeature_set.filter(
            content_type = ct, object_id = object.id).exists()

    def remove_feature(self, object):
        ''' Remove an object from the route. '''

        pf = self.get_route_feature(object)

        next_pfs = self.routefeature_set.filter(index__gt = pf.index)

        for p in next_pfs:
            p.index = p.index-1
            p.save()

        pf.delete()

    def reorder_features(self, indeces):
        # TODO
        pass

    def get_route_feature(self, object):
        ''' Get the route feature container for this object. '''

        ct = ContentType.objects.get_for_model(object)
        pf = get_model('routefeature').objects.get(
            content_type = ct, object_id = object.id)

        return pf
