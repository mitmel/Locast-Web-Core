from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _

from locast.auth.forms import UserCreationForm, UserChangeForm

class LocastUserAdmin(UserAdmin):
    list_display = ('display_name', 'email', 'first_name', 'last_name', 'username', 'is_staff', 'date_joined')

    form = UserChangeForm
    add_form = UserCreationForm
    fieldsets = UserAdmin.fieldsets + ((_('Locast'), {'fields': ('display_name',)}),)
