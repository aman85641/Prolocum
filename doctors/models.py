from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings


class DoctorProfile(models.Model):
    QUALIFICATION_CHOICES = [
        ('mbbs', 'MBBS'),
        ('bams', 'BAMS'),
        ('bhms', 'BHMS'),
    ]
    SEX_CHOICES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    WARD_CHOICES = [
        ('general', 'General Ward'),
        ('icu', 'ICU Ward'),
        ('casualty', 'Casualty Ward'),
        ('female', 'Female Ward'),
    ]

    user            = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    full_name       = models.CharField(max_length=150)
    age             = models.PositiveIntegerField(null=True, blank=True)
    sex             = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)
    registration_no = models.CharField(max_length=50, blank=True)
    qualification   = models.CharField(max_length=10, choices=QUALIFICATION_CHOICES, blank=True)
    experience      = models.CharField(max_length=50, blank=True)
    is_registration_complete = models.BooleanField(default=False)
    # Address
    address         = models.TextField(blank=True)
    state           = models.CharField(max_length=100, blank=True)
    city            = models.CharField(max_length=100, blank=True)
    pincode         = models.CharField(max_length=10, blank=True)
    STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]
    
    upi_id = models.CharField(max_length=100, blank=True)

    verification_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    # Ward preferences (stored as comma-separated)
    ward_preferences = models.CharField(max_length=200, blank=True)

    # Known procedures (stored as comma-separated)
    known_procedures = models.TextField(blank=True)

    # Documents
    profile_photo   = models.ImageField(upload_to='doctors/photos/', null=True, blank=True)
    aadhar_photo    = models.ImageField(upload_to='doctors/aadhar/', null=True, blank=True)
    pan_card        = models.ImageField(upload_to='doctors/pan/', null=True, blank=True)
    degree_photo    = models.ImageField(upload_to='doctors/degree/', null=True, blank=True)
    registered_state = models.CharField(max_length=100, blank=True)

    is_verified     = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.qualification.upper()})"

    def get_ward_list(self):
        return [w.strip() for w in self.ward_preferences.split(',') if w.strip()]

    def get_procedure_list(self):
        return [p.strip() for p in self.known_procedures.split(',') if p.strip()]