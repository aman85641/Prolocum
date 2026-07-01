import random
import requests
from django.conf import settings
from django.core.cache import cache

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(mobile_number, otp_type="signup"):
    otp = generate_otp()
    cache.set(f"otp_{mobile_number}", otp, timeout=600)

    templates = {
        "signup": {
            "id": settings.MSGCLUB_TEMPLATE_SIGNUP,
            "message": f"Welcome to ProLocum! Your Signup OTP is: {otp} This OTP is valid for 10 minutes. Please do not share this code with anyone. - Team ProLocum"
        },
        "login": {
            "id": settings.MSGCLUB_TEMPLATE_LOGIN,
            "message": f"Your ProLocum Login OTP is: {otp} This OTP is valid for 10 minutes. Please do not share this code with anyone. - Team ProLocum"
        },
        "forgot": {
            "id": settings.MSGCLUB_TEMPLATE_FORGOT,
            "message": f"Your ProLocum password reset OTP is: {otp} This OTP is valid for 10 minutes. If you did not request this, please ignore this message. - Team ProLocum"
        },
        "account_verified": {
            "id": settings.MSGCLUB_TEMPLATE_ACCOUNT_VERIFIED,
            "message": f"Hi {mobile_number}, Your ProLocum account verification has been successfully approved. You can now apply for shifts and connect with healthcare providers. - Team ProLocum"
        },
    }

    selected = templates[otp_type]

    url = "http://msg.msgclub.net/rest/services/sendSMS/sendGroupSms"
    params = {
        "AUTH_KEY": settings.MSGCLUB_AUTH_KEY,
        "message": selected["message"],
        "senderId": settings.MSGCLUB_SENDER_ID,
        "routeId": 8,
        "mobileNos": mobile_number,
        "smsContentType": "english",
        "templateid": selected["id"],
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data.get("responseCode") == "3001":
        return True
    return False

def verify_otp(mobile_number, entered_otp):
    saved_otp = cache.get(f"otp_{mobile_number}")
    if saved_otp and saved_otp == entered_otp:
        cache.delete(f"otp_{mobile_number}")
        return True
    return False