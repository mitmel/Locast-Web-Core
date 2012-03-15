from django.http import HttpResponse, HttpResponseNotAllowed

# Allowed HTTP methods
METHODS = sorted(('get','post','head','put','delete','options'))

class ResourceMeta(type):
    def __init__(cls, name, bases, d):
        p = {}
        for m in [x for x in d.keys() if not x.startswith('_')]:
            try:
                p[m] = staticmethod(d[m])
                del d[m]
            except KeyError:
                continue
            else:
                pass
        super(ResourceMeta, cls).__init__(name, bases, d)
        for mn, sm in p.iteritems():
            setattr(cls, mn, sm)

class ResourceView(object):
    __metaclass__ = ResourceMeta

    def __new__(cls, request, *args, **kwargs):
        try:
            method = '_' + kwargs['method']
            del kwargs['method']
        except:
            method = ''

        # The http request method (get, head, put etc.)
        request_method = request.method.lower()

        # The full resource method (get_object)
        resource_method = request_method + method

        if resource_method.startswith('_'):
            return cls.__not_allowed()

        # The actual method object
        class_method = getattr(cls, resource_method, None)

        if not class_method:
            # A hackish way to deal with head requests
            if request_method == 'head' and hasattr(cls, 'get' + method):
                response = getattr(cls, 'get' + method)(request, *args, **kwargs)
                if not isinstance(response, HttpResponse): 
                    return ''
                response.content = ''
                return response
            else:
                return cls.__not_allowed()

        return class_method(request, *args, **kwargs)

    @classmethod
    def __not_allowed(cls):
        allow = []
        for method in METHODS:
            if hasattr(cls, method):
                allow.append(method)
        if 'get' in allow and 'head' not in allow:
            allow.append('head')
        return HttpResponseNotAllowed(k.upper() for k in allow) 

