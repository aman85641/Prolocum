from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('hospital', 'Hospital'),
        ('admin', 'Admin'),
    )
    role   = models.CharField(max_length=20, choices=ROLE_CHOICES)
    mobile = models.CharField(max_length=10, unique=True, null=True, blank=True)  # ✅ Unique mobile

    def __str__(self):
        return f"{self.username} ({self.role})"
    

import random
import requests
from django.db import models
from django.conf import settings

class OTP(models.Model):
    mobile     = models.CharField(max_length=10)
    otp        = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used    = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.mobile} — {self.otp}"

    @staticmethod
    def generate(mobile, otp_type="login"):
        otp_code = str(random.randint(100000, 999999))
        OTP.objects.filter(mobile=mobile).delete()
        OTP.objects.create(mobile=mobile, otp=otp_code)

        try:
            templates = {
    "signup": {
        "id"     : settings.MSGCLUB_TEMPLATE_SIGNUP,
        "message": f"Welcome to ProLocum! Your Signup OTP is: {otp_code} This OTP is valid for 10 minutes. Please do not share this code with anyone. - Team ProLocum"
    },
    "login": {
        "id"     : settings.MSGCLUB_TEMPLATE_LOGIN,
        "message": f"Your ProLocum Login OTP is: {otp_code} This OTP is valid for 10 minutes. Please do not share this code with anyone. - Team ProLocum"
    },
    "forgot": {
        "id"     : settings.MSGCLUB_TEMPLATE_FORGOT,
        "message": f"Your ProLocum password reset OTP is: {otp_code} This OTP is valid for 10 minutes. If you did not request this, please ignore this message. - Team ProLocum"
    },
    "shift_start": {
        "id"     : settings.MSGCLUB_TEMPLATE_SHIFT_START_OTP,
        "message": f"Your Shift Start OTP is: {otp_code} Please provide this OTP to begin your shift. This OTP is valid for one-time use only. - Team ProLocum"
    },
    
}
            selected = templates.get(otp_type, templates["login"])
            print(f"DEBUG: otp_type={otp_type}, selected_template={selected['id']}, message_start={selected['message'][:20]}")

            url = "http://msg.msgclub.net/rest/services/sendSMS/sendGroupSms"
            params = {
                "AUTH_KEY"       : settings.MSGCLUB_AUTH_KEY,
                "message"        : selected["message"],
                "senderId"       : settings.MSGCLUB_SENDER_ID,
                "routeId"        : 8,
                "mobileNos"      : mobile,
                "smsContentType" : "english",
                "templateid"     : selected["id"],
            }
            response = requests.get(url, params=params, timeout=5)
            print(f"SMS Response: {response.text}")

        except Exception as e:
            print(f"SMS Error: {e}")

        print(f"\n{'='*30}")
        print(f"  OTP for {mobile}: {otp_code}")
        print(f"{'='*30}\n")
        return otp_code

from django.conf import settings
from django.db import models

class RegistrationDraft(models.Model):
    user         = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='draft')
    role         = models.CharField(max_length=20)
    current_step = models.IntegerField(default=1)
    step1_data   = models.JSONField(default=dict)
    step2_data   = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.user.mobile} — Step {self.current_step}"