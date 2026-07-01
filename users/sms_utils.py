import requests
from django.conf import settings

def _send_sms(mobile, message, template_id):
    url = "http://msg.msgclub.net/rest/services/sendSMS/sendGroupSms"
    params = {
        "AUTH_KEY"       : settings.MSGCLUB_AUTH_KEY,
        "message"        : message,
        "senderId"       : settings.MSGCLUB_SENDER_ID,
        "routeId"        : 8,
        "mobileNos"      : mobile,
        "smsContentType" : "english",
        "templateid"     : template_id,
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"SMS Response: {response.text}")
        return response.json().get("responseCode") == "3001"
    except Exception as e:
        print(f"SMS Error: {e}")
        return False

def send_welcome_sms(mobile, name):
    msg = f"Hi {name}, Welcome to ProLocum! We're excited to have you onboard. Complete your profile to receive better shift opportunities and faster approvals. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_WELCOME)

def send_account_verified_sms(mobile, name):
    msg = f"Hi {name}, Your ProLocum account verification has been successfully approved. You can now apply for shifts and connect with healthcare providers. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_ACCOUNT_VERIFIED)

def send_password_reset_success_sms(mobile, name):
    msg = f"Hi {name}, Your ProLocum account password has been changed successfully. If you did not perform this action, please contact support immediately. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_PASSWORD_RESET_SUCCESS)

def send_new_shift_sms(mobile, name, position, location, date):
    msg = f"Hi {name}, shift details are available in your ProLocum account. Position: {position} Location: {location} Date: {date} Please login to view details. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_NEW_SHIFT)

def send_application_submitted_sms(mobile, name, shift_name):
    msg = f"Hi {name}, Your application for {shift_name} has been successfully submitted. We'll notify you once the healthcare provider responds. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_APP_SUBMITTED)

def send_application_accepted_sms(mobile, name, shift_name):
    msg = f"Congratulations {name}! Your application for {shift_name} has been accepted. Please check your dashboard for complete shift details. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_APP_ACCEPTED)

def send_application_not_selected_sms(mobile, name, shift_name):
    msg = f"Hi {name}, Thank you for applying for {shift_name}. Unfortunately, this shift has been filled by another candidate. More opportunities will be available soon. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_APP_NOT_SELECTED)

def send_shift_confirmation_sms(mobile, name, hospital, date, time):
    msg = f"Hi {name}, Your shift at {hospital} on {date} at {time} has been successfully confirmed. Please check your dashboard for complete details. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_SHIFT_CONFIRMATION)

def send_shift_reminder_sms(mobile, hospital, shift_time, location):
    msg = f"Reminder: Your upcoming shift at {hospital} starts in 2 hours. Shift Time: {shift_time} Location: {location} Please ensure timely arrival. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_SHIFT_REMINDER)

def send_shift_completed_sms(mobile, name, hospital):
    msg = f"Hi {name}, Your shift at {hospital} has been marked as completed successfully. Payment processing will begin shortly. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_SHIFT_COMPLETED)

def send_payment_paid_sms(mobile, name, amount):
    msg = f"Hi {name}, Payment for your completed shift has been successfully marked as paid. Amount: ₹{amount} Thank you for working with ProLocum. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_PAYMENT_PAID)

def send_emergency_broadcast_sms(mobile, role, location, shift_time):
    msg = f"Emergency requirement nearby! A healthcare provider near your location is urgently looking for a {role} within a 10 km radius. Location: {location} Shift Time: {shift_time} Respond quickly to confirm your availability. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_EMERGENCY)

def send_shift_start_otp(mobile, otp):
    msg = f"Your Shift Start OTP is: {otp} Please provide this OTP to begin your shift. This OTP is valid for one-time use only. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_SHIFT_START_OTP)


def send_shift_arrived_otp(mobile, otp):
    msg = f"Your Shift Start OTP is: {otp} Please provide this OTP to begin your shift. This OTP is valid for one-time use only. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_SHIFT_START_OTP)

def send_shift_start_otp(mobile, otp):
    msg = f"Your Shift Start OTP is: {otp} Please provide this OTP to begin your shift. This OTP is valid for one-time use only. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_SHIFT_START_OTP)

def send_shift_complete_otp(mobile, otp):
    msg = f"Your Shift Start OTP is: {otp} Please provide this OTP to begin your shift. This OTP is valid for one-time use only. - Team ProLocum"
    return _send_sms(mobile, msg, settings.MSGCLUB_TEMPLATE_SHIFT_START_OTP)