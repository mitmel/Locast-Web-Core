import sys, traceback
import settings

from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response
from django.template import RequestContext

from locast.api.exceptions import *
from locast.auth.exceptions import *

class LocastMiddleware(object):
    ''' Middleware which intercepts API and HTTP exceptions and handles them, printing out logging info '''

    def process_exception(self, request, exception):
        retval = None
        is_404 = False

        message = str(exception)

        ######## WEB EXCEPTIONS #########

        # 401 Authentication Required
        if isinstance(exception, HttpAuthenticationError):
            resp = HttpResponse('Authentication Required', status=401)
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
            retval = HttpResponse(content=message, status=400, mimetype='text/plain')

        # 401 Unauthorized
        elif isinstance(exception, APIUnauthorized):
            retval = HttpResponse(content=message, status=401, mimetype='text/plain')

        # 403 Forbidden
        elif isinstance(exception, APIForbidden):
            retval = HttpResponse(content=message, status=403, mimetype='text/plain')

        # 404 Not Found
        elif isinstance(exception, APINotFound):
            retval = HttpResponse(content=message, status=404, mimetype='text/plain')

        #################################

        # 500 Error
        else:
            pass

        is_500 = not retval and not is_404

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

