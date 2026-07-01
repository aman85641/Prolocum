# shifts/models.py

from django.db import models
from django.conf import settings


class Shift(models.Model):
    SHIFT_TYPE_CHOICES = [
        ('single', 'Single Shift'),
        ('multiple', 'Multiple Shift'),
    ]
    WARD_CHOICES = [
        ('general', 'General Ward'),
        ('icu', 'ICU Ward'),
        ('casualty', 'Casualty Ward'),
        ('female', 'Female Ward'),
    ]
    # shifts/models.py

    QUALIFICATION_CHOICES = [
    # Doctor
    ('mbbs', 'MBBS'),
    ('bams', 'BAMS'),
    ('bhms', 'BHMS'),
    ('bams_bhms', 'BAMS/BHMS'),
    # Nurse
    ('gnm', 'GNM'),
    ('bsc_nursing', 'B.Sc Nursing'),
    ('anm', 'ANM'),
    ('msc_nursing', 'M.Sc Nursing'),
]

    posted_by               = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_shifts'
    )
    TARGET_ROLE_CHOICES = [
    ('doctor', 'Doctor'),
    ('nurse', 'Nurse'),
]
    location_link = models.URLField(max_length=500, blank=True, null=True, help_text='Google Maps link')

    target_role = models.CharField(max_length=10, choices=TARGET_ROLE_CHOICES, default='both')
    hospital_name           = models.CharField(max_length=200)
    ward_type               = models.CharField(max_length=20, choices=WARD_CHOICES)
    bed_count               = models.PositiveIntegerField(default=1)
    address                 = models.TextField()
    landmark                = models.CharField(max_length=200, blank=True)
    area                    = models.CharField(max_length=100, blank=True)
    city                    = models.CharField(max_length=100)

    qualification_required  = models.CharField(max_length=20, choices=QUALIFICATION_CHOICES, default='bams_bhms')
    shift_type              = models.CharField(max_length=10, choices=SHIFT_TYPE_CHOICES, default='single')
    start_date              = models.DateField()
    end_date                = models.DateField(null=True, blank=True)
    start_time              = models.TimeField()
    end_time                = models.TimeField()
    pay                     = models.PositiveIntegerField(help_text='Pay in INR')

    requirements            = models.TextField(blank=True)

    is_urgent               = models.BooleanField(default=False)
    is_active               = models.BooleanField(default=True)
    created_at              = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hospital_name} - {self.get_ward_type_display()} ({self.start_date})"

    def get_requirements_list(self):
        return [r.strip() for r in self.requirements.split('\n') if r.strip()]

    @property
    def accepted_count(self):
        return self.applications.filter(status='accepted').count()

    @property
    def reserved_count(self):
        return self.applications.filter(status='reserved').count()


class ShiftApplication(models.Model):
    # ── Poster-set statuses ──────────────────────────────────
    POSTER_STATUS_CHOICES = [
        ('applied',     'Applied'),
        ('accepted',    'Accepted'),
        ('reserved',    'Reserved'),
        ('rejected',    'Rejected'),
        ('withdrawn',   'Withdrawn'),
    ]

    # ── Onboard progress (poster controls after accepting) ───
    ONBOARD_STATUS_CHOICES = [
        ('pending',     'Pending'),     # not yet onboarded
        ('onboarded',   'Onboarded'),   # poster confirmed onboard
        ('arrived',     'Arrived'),
        ('started',     'Started'),
        ('completed',   'Completed'),
    ]

    shift           = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='applications')
    applicant       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shift_applications'
    )

    # Status set by poster (accept / reserve / reject)
    status          = models.CharField(max_length=15, choices=POSTER_STATUS_CHOICES, default='applied')

    # Progress tracking — only meaningful when status='accepted'
    onboard_status  = models.CharField(max_length=15, choices=ONBOARD_STATUS_CHOICES, default='pending')
    accepted_at = models.DateTimeField(null=True, blank=True)
    applied_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    # Payment
    PAYMENT_METHOD_CHOICES = [
        ('upi',  'UPI'),
        ('cash', 'Cash'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid',   'Unpaid'),
        ('paid',     'Paid'),
        ('disputed', 'Disputed'),  # hospital paid, locum ne reject kiya
    ]
    
    payment_method         = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_status         = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    hospital_marked_paid   = models.BooleanField(default=False)  # hospital ne "pay kar diya" kaha
    locum_confirmed_paid   = models.BooleanField(default=False)  # locum ne confirm kiya
    hospital_paid_at       = models.DateTimeField(null=True, blank=True)
    class Meta:
        unique_together = ('shift', 'applicant')

    def __str__(self):
        return f"{self.applicant} → {self.shift} ({self.status})"
    
    def can_withdraw(self):
        if self.status != 'accepted':
            return False, "Only accepted applications can be withdrawn"
        if self.shift.is_urgent:
            return False, "Urgent shift cannot be withdrawn"
        if self.accepted_at:
            from datetime import timedelta
            from django.utils import timezone
            deadline = self.accepted_at + timedelta(minutes=30)
            if timezone.now() > deadline:
                return False, "30 minute withdrawal window has passed"
        return True, "ok"
    
    @property
    def is_onboard_track(self):
        """True jab poster ne accept kiya ho"""
        return self.status == 'accepted'

    @property
    def onboard_step_index(self):
        steps = ['onboarded', 'arrived', 'started', 'completed']
        try:
            return steps.index(self.onboard_status)
        except ValueError:
            return -1


class ShiftReview(models.Model):
    """Doctor hospital ko review karta hai aur hospital doctor ko — dono ek hi model."""
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    REVIEWER_TYPE = [
        ('doctor',   'Doctor → Hospital'),
        ('hospital', 'Hospital → Doctor'),
    ]

    application     = models.ForeignKey(ShiftApplication, on_delete=models.CASCADE, related_name='reviews')
    reviewer        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_reviews'
    )
    reviewer_type   = models.CharField(max_length=10, choices=REVIEWER_TYPE)
    rating          = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment         = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('application', 'reviewer_type')

    def __str__(self):
        return f"{self.reviewer_type} review for {self.application}"