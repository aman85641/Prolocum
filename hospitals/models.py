from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings


class HospitalProfile(models.Model):
    HOSPITAL_TYPE_CHOICES = [
        ('private', 'Private'),
        ('government', 'Government'),
        ('trust', 'Trust / NGO'),
        ('clinic', 'Clinic'),
    ]

    user             = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hospital_profile')
    hospital_name    = models.CharField(max_length=200)
    hospital_type    = models.CharField(max_length=20, choices=HOSPITAL_TYPE_CHOICES, blank=True)
    registration_no  = models.CharField(max_length=100, blank=True)
    is_registration_complete = models.BooleanField(default=False)
    # Contact
    contact_person   = models.CharField(max_length=150, blank=True)
    phone            = models.CharField(max_length=15, blank=True)
    email            = models.EmailField(blank=True)

    # Address
    address          = models.TextField(blank=True)
    state            = models.CharField(max_length=100, blank=True)
    city             = models.CharField(max_length=100, blank=True)
    pincode          = models.CharField(max_length=10, blank=True)

    # Hospital details
    specialities     = models.TextField(blank=True)   # comma-separated
    bed_count        = models.PositiveIntegerField(null=True, blank=True)

   # Documents
    logo             = models.ImageField(upload_to='hospitals/logos/', null=True, blank=True)
    registration_doc = models.FileField(upload_to='hospitals/docs/', null=True, blank=True)
    pan_card         = models.FileField(upload_to='hospitals/pan/', null=True, blank=True)
    aadhar_photo     = models.FileField(upload_to='hospitals/aadhar/', null=True, blank=True)

    registered_state = models.CharField(max_length=100, blank=True)
    is_verified      = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
    STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]
    verification_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    def __str__(self):
        return self.hospital_name

    def get_speciality_list(self):
        return [s.strip() for s in self.specialities.split(',') if s.strip()]
    

# hospitals/vacancy_models.py
# Isko hospitals/models.py mein paste karo (existing code ke neeche)

from django.db import models
from django.conf import settings


class Vacancy(models.Model):
    SHIFT_TYPE_CHOICES = [
        ('single', 'Single Shift'),
        ('multiple', 'Multiple Shift'),
    ]
    STAFF_TYPE_CHOICES = [
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
    ]
    WARD_CHOICES = [
        ('general', 'General Ward'),
        ('icu', 'ICU Ward'),
        ('casualty', 'Casualty Ward'),
        ('female', 'Female Ward'),
        ('pediatric', 'Pediatric Ward'),
        ('maternity', 'Maternity Ward'),
    ]
    DOCTOR_QUALIFICATION_CHOICES = [
        ('mbbs', 'MBBS'),
        ('bams', 'BAMS'),
        ('bhms', 'BHMS'),
        ('bams_bhms', 'BAMS/BHMS'),
    ]
    NURSE_QUALIFICATION_CHOICES = [
        ('gnm', 'GNM'),
        ('bsc_nursing', 'B.Sc Nursing'),
        ('anm', 'ANM'),
        ('msc_nursing', 'M.Sc Nursing'),
    ]
    SHIFT_LABEL_CHOICES = [
    ('morning',    'Morning Shift'),
    ('evening',    'Evening Shift'),
    ('night',      'Night Shift'),
    ('rotational', 'Rotational Shift'),
]

    shift_label = models.CharField(
    max_length=15, 
    choices=SHIFT_LABEL_CHOICES, 
    blank=True, 
    default=''
)
    posted_by       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vacancies')
    hospital_name   = models.CharField(max_length=200)
    location        = models.CharField(max_length=200)
    city            = models.CharField(max_length=100, blank=True)
    state           = models.CharField(max_length=100, blank=True)

    staff_type      = models.CharField(max_length=10, choices=STAFF_TYPE_CHOICES, default='doctor')
    designation     = models.CharField(max_length=100, blank=True)
    ward_type       = models.CharField(max_length=20, choices=WARD_CHOICES, blank=True)
    bed_capacity    = models.PositiveIntegerField(null=True, blank=True)

    # Qualifications
    doctor_qualification = models.CharField(max_length=30, choices=DOCTOR_QUALIFICATION_CHOICES, blank=True)
    nurse_qualification  = models.CharField(max_length=20, choices=NURSE_QUALIFICATION_CHOICES, blank=True)
    experience_required  = models.CharField(max_length=100, blank=True)

    # Shift details
    shift_type      = models.CharField(max_length=10, choices=SHIFT_TYPE_CHOICES, default='single')
    start_date = models.DateField(null=True, blank=True)  
    end_date        = models.DateField(null=True, blank=True)
    start_time      = models.TimeField()
    end_time        = models.TimeField()

    salary          = models.DecimalField(max_digits=10, decimal_places=2)
    job_description = models.TextField(blank=True)
    contact_email   = models.EmailField(blank=True)
    contact_phone   = models.CharField(max_length=15, blank=True)

    is_urgent       = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.hospital_name} - {self.designation} ({self.shift_type})"

    @property
    def accepted_count(self):
        return self.applications.filter(status='accepted').count()

    @property
    def applicant_count(self):
        return self.applications.exclude(status='withdrawn').count()


class VacancyApplication(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    vacancy     = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='applications')
    applicant   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vacancy_applications')
    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default='applied')
    applied_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    note        = models.TextField(blank=True)

    class Meta:
        unique_together = ('vacancy', 'applicant')

    def __str__(self):
        return f"{self.applicant.username} → {self.vacancy.hospital_name} ({self.status})"