import sys, traceback
import settings

from django import http
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response
from django.template import RequestContext

from locast.api.exceptions import APIBadRequest, APIUnauthorized, APIForbidden, APINotFound, APIConflict
from locast.auth.exceptions import HttpAuthenticationError


class LocastMiddleware(object):
    ''' Middleware which intercepts API and HTTP exceptions and handles them, printing out logging info '''

    def process_exception(self, request, exception):
        retval = None
        is_404 = False

        message = str(exception)

        ######## WEB EXCEPTIONS #########

        # 401 Authentication Required
        if isinstance(exception, HttpAuthenticationError):
            resp = http.HttpResponse('Authentication Required', status=401)
            resp['WWW-Authenticate'] = 'Basic realm="User Authentication"'
            retval = resp

        # 403 Permission Denied
        elif isinstance(exception, PermissionDenied):
            message = 'Permission Denied'
            retval = render_to_response('403.html', locals(), context_instance=RequestContext(request))

        # 404 Error
        # This will be handled automatically by django
        elif isinstance(exception, Http404):
            is_404 = True

        ######## API EXCEPTIONS #########
        
        # 400 Bad Request
        elif isinstance(exception, APIBadRequest):
            retval = http.HttpResponseBadRequest(content=message, mimetype='text/plain')

        # 401 Unauthorized
        elif isinstance(exception, APIUnauthorized):
            retval = http.HttpResponse(content=message, status=401, mimetype='text/plain')

        # 403 Forbidden
        elif isinstance(exception, APIForbidden):
            retval = http.HttpResponseForbidden(content=message, mimetype='text/plain')

        # 404 Not Found
        elif isinstance(exception, APINotFound):
            retval = http.HttpResponseNotFound(content=message, mimetype='text/plain')

        # 409 Conflict
        elif isinstance(exception, APIConflict):
            retval = http.HttpResponse(content=message, status=409, mimetype='text/plain')

        #################################

        # 500 Error
        else:
            pass

        is_500 = not retval and not is_404

        # Print a log message if debug is turned on, always print 500s
        if settings.DEBUG or is_500:
            print

            if is_500:
                print '*********** 500 ***********'

            print '********** ERROR **********'
            print exception.__class__.__name__  + ' (' + unicode(message) + ')'
            traceback.print_exc(file=sys.stdout)
            print
            print 'REMOTE_ADDR: ' + request.META['REMOTE_ADDR'] 
            print 'REMOTE_USER: ' 

            if 'REMOTE_USER' in request.META:
                print request.META['REMOTE_USER'] 

            print 'REQUEST_USER: ' + request.user.__unicode__()
            print 'REQUEST_METHOD: ' + request.META['REQUEST_METHOD']

            if 'REQUEST_URI' in request.META:
                print 'REQUEST_URI: ' + request.META['REQUEST_URI']

            print 'GET: ' + str(request.GET)
            print 'POST: ' + str(request.POST)
            print '***************************'
            print 

        return retval
 

# Based on: https://gist.github.com/jessykate/2941258
class CORSMiddleware(object):
    '''
    This middleware allows cross-domain XHR using the html5 postMessage API.

    eg.
    Access-Control-Allow-Origin: http://foo.example
    Access-Control-Allow-Methods: POST, GET, OPTIONS, PUT, DELETE
    Access-Control-Allow-Headers: ["Content-Type"]
    '''

    # Default settings
    CORS_ALLOWED_ORIGINS = '*'
    CORS_ALLOWED_METHODS = ['POST','GET','PUT','HEAD','DELETE','OPTIONS']
    CORS_ALLOWED_HEADERS = ['ORIGIN', 'CONTENT_TYPE']

    def __init__(self):
        # OVerride defaults
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
            self.CORS_ALLOWED_ORIGINS = settings.CORS_ALLOWED_ORIGINS
        if hasattr(settings, 'CORS_ALLOWED_METHODS'):
            self.CORS_ALLOWED_METHODS = settings.CORS_ALLOWED_METHODS
        if hasattr(settings, 'CORS_ALLOWED_HEADERS'):
            self.CORS_ALLOWED_HEADERS = settings.CORS_ALLOWED_HEADERS

    def process_request(self, request):
        if request.method == 'OPTIONS':
            response = http.HttpResponse()

            if 'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META:
                response['Access-Control-Allow-Methods'] = ','.join(self.CORS_ALLOWED_METHODS)

            if 'HTTP_ACCESS_CONTROL_REQUEST_HEADERS' in request.META:
                response['Access-Control-Allow-Headers']  = ','.join(self.CORS_ALLOWED_HEADERS)

            return response
 
        return None
 
    def process_response(self, request, response):

        # If it's already been set, just return the response
        if response.has_header('Access-Control-Allow-Origin'):
            return response

        if not response.has_header('Access-Control-Allow-Methods'):
            response['Access-Control-Allow-Methods'] = ",".join(self.CORS_ALLOWED_METHODS)

        response['Access-Control-Allow-Origin']  = self.CORS_ALLOWED_ORIGINS 

        return response
