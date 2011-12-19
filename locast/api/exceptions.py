# 400
class APIBadRequest(Exception): pass

# 401
class APIUnauthorized(Exception): pass

#403
class APIForbidden(Exception): pass

# 404
class APINotFound(Exception): pass


class InvalidParameterException(Exception): pass
