from django.contrib import admin

# Register your models here.
# admin/admin.py mein add karo

from .models import City

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display  = ['name', 'state']
    list_filter   = ['state']
    search_fields = ['name', 'state']
    ordering      = ['state', 'name']