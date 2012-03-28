from django.contrib.auth import authenticate

from locast.auth.exceptions import HttpAuthenticationError


def _http_auth(request):
    ''' 
    Takes in a http request and authenticates using basic http authentication 
    credentials, returning a user.
    '''

    user = None

    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()

        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                uname, passwd = auth[1].decode('base64').split(':')
                user = authenticate(username=uname, password=passwd)
                if not user:
                    raise HttpAuthenticationError
    
    return user


def optional_http_auth(view_func):
    ''' Checks for basic http auth credentials but does not require them '''

    def _auth(request, *args, **kwargs):
        if request.user and request.user.is_authenticated():
            return view_func(request, *args, **kwargs)

        user = _http_auth(request)

        if user and user.is_active:
            request.user = user
            return view_func(request, *args, **kwargs)

        return view_func(request, *args, **kwargs)

    return _auth


def require_http_auth(view_func):
    ''' Decorator which requires a method to be accessed using http credentials '''

    def _auth(request, *args, **kwargs):
        if request.user and request.user.is_authenticated():
            return view_func(request, *args, **kwargs)

        user = _http_auth(request)

        if user and user.is_active:
            request.user = user
            return view_func(request, *args, **kwargs)

        else:
            raise HttpAuthenticationError
    
    return _auth

