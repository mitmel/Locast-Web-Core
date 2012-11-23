import random

def random_string(chars, length):
    ''' Generate a random string. '''

    auth_secret = ''.join([random.choice(chars) for i in range(length)])
    return auth_secret
