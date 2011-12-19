class HttpAuthenticationError(Exception):
    ''' Raised with invalid basic http auth credentials '''
    pass

class PairingException(Exception):
    ''' Used in locast.models.modelbases.LocastUserManager '''
    pass
