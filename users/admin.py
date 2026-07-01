from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # List page mein yeh columns dikhenge
    list_display = ('username', 'email', 'mobile', 'role', 'is_active', 'date_joined')  # ← mobile add karo
    
    # Filter sidebar
    list_filter = ('role', 'is_active', 'is_staff')
    
    # Search
    search_fields = ('username', 'email')
    
    # Ordering
    ordering = ('-date_joined',)

    # User edit page mein role field add karo
    fieldsets = UserAdmin.fieldsets + (
        ('Role Info', {
            'fields': ('role',)
        }),
    )
    fieldsets = UserAdmin.fieldsets + (
    ('Role Info', {
        'fields': ('role', 'mobile')  # ← mobile add karo
    }),
)

    add_fieldsets = UserAdmin.add_fieldsets + (
    ('Role Info', {
        'fields': ('role', 'mobile')  # ← mobile add karo
    }),
)
    # Naya user banate waqt role dikhaye
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Info', {
            'fields': ('role',)
        }),
    )