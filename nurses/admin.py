from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import NurseProfile


@admin.register(NurseProfile)
class NurseProfileAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'get_username', 'qualification', 'registration_no',
        'city', 'state', 'verification_status', 'is_registration_complete', 'created_at'
    ]
    list_filter = ['verification_status', 'qualification', 'sex', 'is_registration_complete', 'state']
    search_fields = ['full_name', 'registration_no', 'city', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Personal Info', {
            'fields': ('full_name', 'age', 'sex', 'qualification', 'experience', 'registration_no')
        }),
        ('Address', {
            'fields': ('address', 'state', 'city', 'pincode')
        }),
        ('Preferences', {
            'fields': ('ward_preferences', 'known_procedures', 'registered_state')
        }),
        ('Documents', {
            'fields': ('profile_photo', 'aadhar_photo', 'pan_card', 'degree_photo')
        }),
        ('Status', {
            'fields': ('verification_status', 'is_registration_complete', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    actions = ['approve_nurses', 'reject_nurses']

    def approve_nurses(self, request, queryset):
        queryset.update(verification_status='approved', is_verified=True)
        self.message_user(request, f"{queryset.count()} nurse(s) approved.")
    approve_nurses.short_description = "✅ Approve selected nurses"

    def reject_nurses(self, request, queryset):
        queryset.update(verification_status='rejected', is_verified=False)
        self.message_user(request, f"{queryset.count()} nurse(s) rejected.")
    reject_nurses.short_description = "❌ Reject selected nurses"