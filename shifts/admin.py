from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Shift, ShiftApplication

admin.site.register(Shift)
admin.site.register(ShiftApplication)