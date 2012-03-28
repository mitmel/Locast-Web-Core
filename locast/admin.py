from django.contrib.gis import admin

class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('time', 'user', 'action', 'content_type', 'content_object')

class FlagAdmin(admin.ModelAdmin):
    list_display = ('content_type','object_id', 'content_object')
    list_filter = ('content_type',)

