from datetime import datetime
import json

from django.contrib.gis.geos import Polygon
from django.core import serializers
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.http import HttpResponse, QueryDict

from locast.api import exceptions

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Content should be a python object of json serializable types
def APIResponseOK(content=None, pg = 1, total = None):
    '''
    An API friendly wrapper for a 200 HttpResponse object, used to return
    a collection of objects in json format

    Arguments:

        content
            A collection of objects. Must be json serializable.
        
        pg
            (optional) the page, if this is part of a paginated collection

        total
            (optional) total number of objects, if this is part of a paginated
            collection
    '''

    content = json.dumps(content)
    resp = HttpResponse(status=200, mimetype='application/json; charset=utf-8', content=content)

    if total:
        resp.__setitem__('X-Object-Total', str(total))
        resp.__setitem__('X-Page-Number', str(pg))

    return resp


def APIResponseCreated(content=None, location=''):
    '''
    API wrapper for 201 HttpResonse (created)

    Arguments:

        content
            The object that was created. Must be JSON serializable

        location
            The location (url) where this object can be located
    '''

    content = json.dumps(content)
    resp = HttpResponse(status=201, mimetype='application/json; charset=utf-8', content=content)
    resp['Location'] = location
    return resp


def api_serialize(obj, request = None, fields = ()):
    '''
    Method used to serialize models. Iterates through all of the parent
    interfaces, joining together the results of _api_serialize methods 
    of these into a dictionary, then joins this with the result 
    of the api_serialize method of the model itself. Returns a 
    standard python dictionary.

    Arguments:

        request
            Django http request object

        fields
            Name of fields to auto serialize
    '''

    # Each of the parent interfaces
    bases = obj.__class__.__bases__

    # Dict made from summation of dicts from _api_serialize (parent interfaces)
    parent_ser_dict = {} 

    # Dict made from the model itself
    model_ser_dict = {} 

    # Tuple made from summation of _api_fields
    fields = ()
    fields_dict = {}

    # Init
    if hasattr(obj, 'api_serialize'):
        model_ser_dict = obj.api_serialize(request)
        if model_ser_dict == None:
            raise Exception('api_serialize returned no dictionary')

    if hasattr(obj, 'api_fields'):
        fields = obj.api_fields

    if hasattr(obj, 'id'): 
        parent_ser_dict['id'] = obj.id

    # One level deep, chain together serialization results from parents.
    for cls in bases:
        if hasattr(cls, '_api_serialize'):
            d = cls._api_serialize(obj, request)
            if d == None:
                raise Exception(str(cls) + ' _api_serialize returned no dictionary')

            parent_ser_dict.update(d)

        elif hasattr(cls, '_api_fields'):
            fields += cls._api_fields;

    # Set the absolute url, if it exists
    if hasattr(obj, 'get_absolute_url'): 
        # Allows overring of default django absolute urls
        abs_url = obj.get_absolute_url()
        if abs_url: 
            parent_ser_dict['url'] = abs_url

    # Set the the api uri
    if hasattr(obj, 'get_api_uri'): 
        parent_ser_dict['uri'] = obj.get_api_uri()

    # If there were fields to auto serialize, do it
    if len(fields) > 0:
        serialized = serializers.serialize('python', [obj], fields=fields)
        # Dict made from auto serialization based on _api_fields

        for s in serialized:
            fields = s['fields']
            fields_dict = fields
            fields_dict['id'] = s['pk']

    # model_ser_dict gets precidence, then parent_ser_dict, then auto fields.
    fields_dict.update(parent_ser_dict)
    fields_dict.update(model_ser_dict)
    return fields_dict


def paginate(objs, request_dict):
    '''
    Paginates a collection of objects based in a request object dictionary
    (request.GET or request.POST)

    Arguments:

        objs
            The collection of objects to paginate

        request_dict
            Dictionary of request parameters
    '''

    pg = 1
    total = len(objs)

    # Paginate the results.
    if 'pagesize' in request_dict:

        pgsize=None

        try:
            pgsize = int(request_dict['pagesize'])
            if 'page' in request_dict:
                pg = int(request_dict['page'])

            if pgsize < 1 or pg < 1:
                raise ValueError
        except ValueError, e:
            raise exceptions.InvalidParameterException('Invalid page number')

        p = Paginator(objs, pgsize)
        try:
            objs = p.page(pg).object_list
        except EmptyPage:
            raise exceptions.APIBadRequest('Empty Page')

    return objs, total, pg


def form_validate(formclass, data, instance=None, commit=True):
    '''
    Uses a form to validate data passed in as a dictionary. See
    http://docs.djangoproject.com/en/dev/ref/forms/validation/

    Arguments:
    
        formclass
            The class of the form to use

        data
            A dictionary of data

        instance
            An existing instance to use to validate
    '''

    qd = QueryDict({}).copy()
    qd.update(data)

    form = formclass(qd, instance=instance)

    if not form.is_valid():
        # If a uuid conflict is the issue, add the conflicting uri to the error message
        if 'uuid' in form.errors:
            conflicting = form._meta.model.objects.get(uuid = data['uuid'])
            if conflicting and hasattr(conflicting, 'get_api_uri'):
                form.errors['uri'] = conflicting.get_api_uri()

        raise exceptions.APIBadRequest(json.dumps(form.errors))

    return form.save(commit=commit)


def get_json(raw_data):
    data = None

    try:
        data = json.loads(raw_data)
    except ValueError:
        raise exceptions.APIBadRequest('Invalid JSON')

    return data


def get_object(modelclass, id, select_related = False):
    '''
    Simple utility that will get an object or raise an APINotFound exception.

    Arguments:
        modelclass -  The class of the model
        id - the id of the object
    '''

    obj = None
    try:
        if select_related:
            obj = modelclass.objects.select_related().get(id=id)
        else:
            obj = modelclass.objects.get(id=id)
    except modelclass.DoesNotExist:
        raise exceptions.APINotFound

    return obj


def strtodate(str):
    '''Returns a date object from a string based on the DATE_FORMAT defined above.'''

    return datetime.strptime(str, DATE_FORMAT)


def datetostr(date):
    '''Returns a string from a date object based on the DATE_FORMAT defined above.'''

    return date.strftime(DATE_FORMAT)


# TODO: This should be deprecated. can just use
# QueryDict.get(key, None)
def get_param(dict, param):
    '''Simple utility to get a value out of a dict, or return None. Avoids KeyErrors'''

    if param in dict and dict[param]:
        return dict[param]
    return None


# Takes in a geometry object and property dictionary
# Returns geojson
def geojson_serialize(obj, geometry, request):
    d = dict(type = 'Feature', id = obj.id) 

    d['geometry'] = json.loads(geometry.geojson)
    if hasattr(obj, 'geojson_properties'):
        d['properties'] = obj.geojson_properties(request)
    return d

# Take in a string of coordinates and return a query object that checks
# if a point is within it Q(location__within=poly)
#
# field is the field that represents a point coordinate e.g. location

def get_polygon_bounds_query(bounds_str, field):
    pnts = bounds_str.split(',')

    if len(pnts) != 4:
        raise ValueError('bounds_str incorrectly formatted! Should be: x1,y1,x2,y2')

    bbox = (float(pnts[0]), float(pnts[1]), 
            float(pnts[2]), float(pnts[3]))

    poly = Polygon.from_bbox(bbox)
    poly.set_srid(4326)

    return Q(**{field + '__within': poly})
