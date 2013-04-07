from locast.api import APIResponseOK, get_param
from locast.api.exceptions import APIBadRequest

def post_favorite(request, object):
    favorite = get_param(request.POST, 'favorite')

    if not favorite:
        raise APIBadRequest('Incorrect data posted. Should be favorite=true or favorite=false.')

    favorite = (favorite in ['true','True'])

    if favorite:
        object.favorite(request.user)
    else:
        object.unfavorite(request.user)

    return APIResponseOK(content={'is_favorite':object.is_favorited_by(request.user)})
