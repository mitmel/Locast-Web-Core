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
        resource_method = request.method.lower() + method
        if resource_method.startswith('_'):
            return cls.__not_allowed()
        return getattr(cls, resource_method, cls.__no_method)(request, *args, **kwargs)

    @classmethod
    def __not_allowed(cls):
        allow = []
        for method in METHODS:
            if hasattr(cls, method):
                allow.append(method)
        if 'get' in allow and 'head' not in allow:
            allow.append('head')
        return HttpResponseNotAllowed(k.upper() for k in allow) 

    @classmethod
    def __no_method(cls, request, *args, **kwargs):
        if request.method == 'HEAD' and hasattr(cls, 'get'):
            return cls.__default_head(request, *args, **kwargs)
        else:
            return cls.__not_allowed()

    @classmethod
    def __default_head(cls, request, *args, **kwargs):
        response = cls.get(request, *args, **kwargs)
        if not isinstance(response, HttpResponse): 
            return ''
        response.content = ''
        return response

