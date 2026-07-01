from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import HospitalProfile


@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    list_display = [
        'hospital_name', 'get_username', 'hospital_type', 'registration_no',
        'contact_person', 'phone', 'city', 'state',
        'bed_count', 'verification_status', 'is_registration_complete', 'created_at'
    ]
    list_filter = ['verification_status', 'hospital_type', 'is_registration_complete', 'state']
    search_fields = ['hospital_name', 'registration_no', 'city', 'phone', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Hospital Info', {
            'fields': ('hospital_name', 'hospital_type', 'registration_no', 'bed_count', 'specialities')
        }),
        ('Contact', {
            'fields': ('contact_person', 'phone', 'email')
        }),
        ('Address', {
            'fields': ('address', 'state', 'city', 'pincode', 'registered_state')
        }),
        ('Documents', {
            'fields': ('logo', 'registration_doc', 'pan_card')
        }),
        ('Status', {
            'fields': ('verification_status', 'is_registration_complete', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    actions = ['approve_hospitals', 'reject_hospitals']

    def approve_hospitals(self, request, queryset):
        queryset.update(verification_status='approved', is_verified=True)
        self.message_user(request, f"{queryset.count()} hospital(s) approved.")
    approve_hospitals.short_description = "✅ Approve selected hospitals"

    def reject_hospitals(self, request, queryset):
        queryset.update(verification_status='rejected', is_verified=False)
        self.message_user(request, f"{queryset.count()} hospital(s) rejected.")
    reject_hospitals.short_description = "❌ Reject selected hospitals"



from .models import HospitalProfile, Vacancy, VacancyApplication

@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = [
        'hospital_name', 'staff_type', 'shift_label', 'designation',
        'city', 'start_date', 'salary', 'is_urgent', 'is_active', 'created_at'
    ]
    list_filter = ['staff_type', 'shift_label', 'shift_type', 'is_urgent', 'is_active', 'ward_type']
    search_fields = ['hospital_name', 'city', 'designation']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Hospital Info', {
            'fields': ('posted_by', 'hospital_name', 'location', 'city', 'state', 'contact_email', 'contact_phone')
        }),
        ('Staffing', {
            'fields': ('staff_type', 'designation', 'ward_type', 'bed_capacity', 'doctor_qualification', 'nurse_qualification', 'experience_required')
        }),
        ('Schedule', {
            'fields': ('shift_type', 'shift_label', 'start_date', 'end_date', 'start_time', 'end_time')
        }),
        ('Compensation', {
            'fields': ('salary', 'job_description', 'is_urgent', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(VacancyApplication)
class VacancyApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'vacancy', 'status', 'applied_at']
    list_filter  = ['status']
    search_fields = ['applicant__username', 'vacancy__hospital_name']