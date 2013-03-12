from django.contrib.auth.admin import UserAdmin

class LocastUserAdmin(UserAdmin):
    list_display = ('display_name', 'email', 'first_name', 'last_name', 'username', 'is_staff', 'date_joined')

    #fieldsets = UserAdmin.fieldsets + ((_('Locast'), {'fields': ('display_name',)}),)
