# A wrapper for django cache with support for cache groups

import hashlib

from django.core.cache import cache

def _cache_key(key, cache_group = None):
    combined_key = ''
    if cache_group:
        group_val = cache.get(cache_group)
        if not group_val:
            group_val = 1
            cache.set(cache_group, group_val)

        combined_key = cache_group + str(cache.get(cache_group, 1)) + ':'

    combined_key += key
    hashed_key = hashlib.md5(combined_key).hexdigest()

    return hashed_key

def incr_group(cache_group):
    '''
    Invalidate the previous group
    '''
    if cache.get(cache_group):
        cache.incr(cache_group)

def set_cache(key, value, cache_group=None):
    key = _cache_key(key, cache_group)
    cache.set(key, value)

def get_cache(key, cache_group=None):
    key = _cache_key(key, cache_group)
    return cache.get(key)

# TODO: if passed a query_dict, ignore all query parameters
# not in the query_dict

def request_cache_key(request, user_specific = False, ignore_params = None):
    '''
    Creates a cache key out of a request

    Arguments:

        request
            The request to use to create a key

        user_specific (optional)
            Whether or not to take into account the user making the request

        ignore_params (optional)
            Parameters to ignore when creating the url-based key

        cache_group (optional)
            The cache group that this value will belong to
    '''

    qd = request.GET.copy()

    if ignore_params:
        for param in ignore_params:
            if param in qd:
                del qd[param]

    key = request.path + qd.urlencode()

    # If a user specific key is requested, create one
    if user_specific and request.user.is_authenticated():
        key = key +'_' + str(request.user.id)

    return key
