from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings


class NurseProfile(models.Model):
    SEX_CHOICES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    QUALIFICATION_CHOICES = [
        ('gnm', 'GNM'),
        ('bsc_nursing', 'B.Sc Nursing'),
        ('anm', 'ANM'),
        ('msc_nursing', 'M.Sc Nursing'),
    ]
    upi_id = models.CharField(max_length=100, blank=True)

    WARD_CHOICES = [
        ('general', 'General Ward'),
        ('icu', 'ICU Ward'),
        ('casualty', 'Casualty Ward'),
        ('female', 'Female Ward'),
        ('pediatric', 'Pediatric Ward'),
        ('maternity', 'Maternity Ward'),
    ]

    user            = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nurse_profile')
    full_name       = models.CharField(max_length=150)
    age             = models.PositiveIntegerField(null=True, blank=True)
    sex             = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)
    registration_no = models.CharField(max_length=50, blank=True)
    qualification   = models.CharField(max_length=20, choices=QUALIFICATION_CHOICES, blank=True)
    experience      = models.CharField(max_length=50, blank=True)
    is_registration_complete = models.BooleanField(default=False)
    # Address
    address         = models.TextField(blank=True)
    state           = models.CharField(max_length=100, blank=True)
    city            = models.CharField(max_length=100, blank=True)
    pincode         = models.CharField(max_length=10, blank=True)

    ward_preferences = models.CharField(max_length=200, blank=True)
    known_procedures = models.TextField(blank=True)
    STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]
    verification_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    # Documents
    profile_photo   = models.ImageField(upload_to='nurses/photos/', null=True, blank=True)
    aadhar_photo    = models.ImageField(upload_to='nurses/aadhar/', null=True, blank=True)
    pan_card        = models.ImageField(upload_to='nurses/pan/', null=True, blank=True)
    degree_photo    = models.ImageField(upload_to='nurses/degree/', null=True, blank=True)
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