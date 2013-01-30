import settings
import smtplib

from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.db import models
from django.utils.translation import ugettext_lazy as _

from managers import UserConfirmationManager

class UserConfirmation(models.Model):

    class Meta:
        verbose_name = _('User confirmation')
        verbose_name_plural = _('User confirmations')

    objects = UserConfirmationManager()

    user = models.OneToOneField(settings.USER_MODEL)
    key = models.CharField(max_length=90)

    def send_confirmation_email(self, subject, reply_email=None, confirm_view='confirm_user', template='user_confirmation_email.django.html'):
        '''
        Create confirmation email sent to user at registration
        '''

        site = Site.objects.get_current()
        site_name = site.name

        if not reply_email:
            reply_email = 'no-reply@' + site.domain

        user = self.user
        confirmation_link = settings.HOST + reverse(confirm_view) + '?key=' + self.key

        text = render_to_string(template, locals())

        try:
            send_mail(subject, text, reply_email, [self.user.email], fail_silently=False)
        except smtplib.SMTPException:
            pass
