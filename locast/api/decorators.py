from django.http import HttpResponseNotAllowed

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

