# A wrapper for django cache which has cache groups

import hashlib

from django.core.cache import cache

def generate_cache_key(key, group=None):
    combined_key = ''
    if group:
        group_val = cache.get(group)
        if not group_val:
            group_val = 1
            cache.set(group, group_val)

        combined_key = group + str(cache.get(group, 1)) + ':'

    combined_key += key
    hashed_key = hashlib.md5(combined_key).hexdigest()

    return hashed_key

def incr_group(group):
    """
    Invalidate an entire group
    """
    if cache.get(group):
        cache.incr(group)

def set(key, value, group=None):
    key = generate_cache_key(key, group)
    cache.set(key, value)

def get(key, group=None):
    key = generate_cache_key(key, group)
    return cache.get(key)

