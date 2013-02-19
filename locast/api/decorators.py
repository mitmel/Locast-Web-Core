from django.http import HttpResponseNotAllowed
from locast.api.cache import request_cache_key, get_cache, set_cache

def allow_method(method):
    ''' Only allow requests of a given method. '''

    def _check(view_func):
        def _check_method(request, *args, **kwargs):
            m = request.method
            if m == method:
                return view_func(request, *args, **kwargs)
            method_list = [method]
            resp = HttpResponseNotAllowed(method_list)
            return resp
        return _check_method
    return _check

def cache_api_response(user_specific = False, ignore_params = None, cache_group = None):
    '''
    Cache a response to an API query 

    Arguments:

        user_specific (optional)
            Whether or not to take into account the user making the request

        ignore_params (optional)
            Parameters to ignore when creating the url-based key

        cache_group (optional)
            The cache group that this value will belong to
    '''

    def _cached_view(view_func):

        def _cache_response(request, *args, **kwargs):
            key = request_cache_key(request, user_specific = user_specific, ignore_params = ignore_params)
            cache = get_cache(key, cache_group = cache_group)
            if cache:
                return cache

            resp = view_func(request, *args, **kwargs)
            if resp.status_code == 200:
                set_cache(key, resp, cache_group = cache_group)

            return resp

        return _cache_response
 
    return _cached_view
