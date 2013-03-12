from django.contrib.gis import admin


class UserConfirmationAdmin(admin.ModelAdmin):
    list_display = ('user', 'key')
