from django.shortcuts import render_to_response
from django.template import RequestContext

from locast.userconfirmation.models import UserConfirmation

def confirm_user(request, template_name='user_confirm.django.html'):

    user = None

    # Find user based on the key
    key = request.GET.get('key', None)
    if key:
        try:
            user = UserConfirmation.objects.get_user_by_key(key)
            uc = UserConfirmation.objects.get(user=user)

            # Activate user
            user.is_active = True
            user.save()

            uc.delete()

        # If key is incorrect, user will be null
        except UserConfirmation.DoesNotExist:
            pass

    return render_to_response(template_name, locals(), context_instance = RequestContext(request))
