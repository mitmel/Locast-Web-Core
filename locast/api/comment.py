from locast import get_model
from locast.api import *


def get_comments(request, object, comment_id=None):
    comment_model = get_model('comment')

    if comment_id:
        comment = check_comment(object, comment_id)
        return APIResponseOK(content=api_serialize(comment))

    comments = comment_model.objects.get_comments(object)
    comments, total, pg = paginate(comments, request.GET)

    comment_arr=[]
    for c in comments:
        comment_arr.append(api_serialize(c))

    return APIResponseOK(content=comment_arr, total=len(comment_arr), pg=pg)


def post_comment(request, object):
    comment = None

    json = get_json(request.body)

    content = get_param(json, 'content')
    if content:
        comment = object.comment(request.user, content)

    return APIResponseCreated(content=api_serialize(comment)) 


def check_comment(object, comment_id):
    comment = None
    try:
        comment = object.comments.get(id=comment_id)
    except comment_model.DoesNotExist:
        raise exceptions.APIBadRequest('Comment is not part of this object')

    return comment
