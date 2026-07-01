from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# Role config
ROLE_CONFIG = {
    'doctor': {
        'label': 'Doctor',
        'icon': '🩺',
        'has_subtypes': True,
        'redirect': 'doctor_dashboard',   # doctors app ka URL name
    },
    'nurse': {
        'label': 'Nurse',
        'icon': '💉',
        'has_subtypes': False,
        'redirect': 'nurse_dashboard',
    },
    'hospital': {
        'label': 'Hospital',
        'icon': '🏥',
        'has_subtypes': False,
        'redirect': 'hospital_dashboard',
    },
    'admin': {
        'label': 'Admin',
        'icon': '⚙',
        'has_subtypes': False,
        'redirect': 'admin:index',
    },
}

DOCTOR_TYPES = {
    'mbbs': 'MBBS',
    'bams': 'BAMS / BHMS',
}


def home(request):
    """Landing page — role selector."""
    return render(request, 'users/home.html')


def login_view(request, role):
    from users.models import OTP
    config = ROLE_CONFIG.get(role, {'label': role.title(), 'icon': ''})
    error = None

    if request.method == 'POST':
        login_type = request.POST.get('login_type')

        # ══ OTP Login ══
        if login_type == 'otp':
            mobile = request.POST.get('mobile', '').strip()
            if len(mobile) != 10 or not mobile.isdigit():
                error = '❌ Enter a valid 10 digit mobile number'
            else:
                existing = User.objects.filter(mobile=mobile).first()
                
                # ✅ BAN CHECK — OTP bhejne se pehle
                if existing and not existing.is_active:
                    error = '🚫 Your account has been deactivated. Please contact support.'
                    return render(request, 'users/login.html', {
                        'role': role, 'role_label': config['label'],
                        'role_icon': config['icon'], 'error': error,
                    })
                
                if existing and existing.role != role:
                    error = f'❌ This number is already registered as {existing.role}'
                else:
                    otp_type = "login" if existing else "signup"
                    OTP.generate(mobile, otp_type=otp_type)
                    request.session['otp_mobile'] = mobile
                    request.session['otp_role']   = role
                    return redirect('verify_otp')

        # ══ Password Login ══
        elif login_type == 'password':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')

            try:
                user_obj = User.objects.get(username=username)
            except User.DoesNotExist:
                error = '❌ Username does not exist'
                return render(request, 'users/login.html', {
                    'role': role, 'role_label': config['label'],
                    'role_icon': config['icon'], 'error': error,
                })

            # ✅ BAN CHECK — authenticate se pehle
            if not user_obj.is_active:
                error = '🚫 Your account has been deactivated. Please contact support.'
                return render(request, 'users/login.html', {
                    'role': role, 'role_label': config['label'],
                    'role_icon': config['icon'], 'error': error,
                })

            user = authenticate(request, username=username, password=password)
            if user is None:
                error = '❌ Incorrect password'
                return render(request, 'users/login.html', {
                    'role': role, 'role_label': config['label'],
                    'role_icon': config['icon'], 'error': error,
                })

            if user.role != role:
                error = f'❌ This account belongs to {user.role}, not {role}'
                return render(request, 'users/login.html', {
                    'role': role, 'role_label': config['label'],
                    'role_icon': config['icon'], 'error': error,
                })

            if user.role == 'admin':
                login(request, user)
                return redirect('admin_dashboard')

            if user.role == 'doctor':
                try:
                    profile = user.doctor_profile
                    status  = profile.verification_status
                except:
                    error = '❌ Doctor profile not found'
                    return render(request, 'users/login.html', {
                        'role': role, 'role_label': config['label'],
                        'role_icon': config['icon'], 'error': error,
                    })

            elif user.role == 'nurse':
                try:
                    profile = user.nurse_profile
                    status  = profile.verification_status
                except:
                    error = '❌ Nurse profile not found'
                    return render(request, 'users/login.html', {
                        'role': role, 'role_label': config['label'],
                        'role_icon': config['icon'], 'error': error,
                    })

            elif user.role == 'hospital':
                try:
                    profile = user.hospital_profile
                    status  = profile.verification_status
                except:
                    error = '❌ Hospital profile not found'
                    return render(request, 'users/login.html', {
                        'role': role, 'role_label': config['label'],
                        'role_icon': config['icon'], 'error': error,
                    })

            if status == 'approved':
                login(request, user)
                return redirect(f'{user.role}_dashboard')
            elif status == 'pending':
                login(request, user)
                return render(request, 'users/verification_pending.html', {
                    'role': role, 'profile': profile,
                })
            elif status == 'rejected':
                return render(request, 'users/verification_pending.html', {
                    'role': role, 'profile': profile, 'rejected': True,
                })

    return render(request, 'users/login.html', {
        'role':       role,
        'role_label': config['label'],
        'role_icon':  config['icon'],
        'error':      error,
    })

def logout_view(request):
    logout(request)
    return redirect('home')

def doctor_type_view(request):
    """Doctor sub-role selection page (MBBS / BAMS)."""
    return render(request, 'users/doctor_type.html')


# Placeholder — replace with your real view
def phone_preview(request):
    return render(request, 'users/medbridge_phone.html')

import secrets
from django.contrib.auth import get_user_model

User = get_user_model()

def forgot_password(request):
    error = None

    if request.method == 'POST':
        step = request.POST.get('step', '1')

        # ── Step 1: Mobile number enter karo, OTP bhejo ──
        if step == '1':
            mobile = request.POST.get('mobile', '').strip()
            if len(mobile) != 10 or not mobile.isdigit():
                error = '❌ Enter a valid 10 digit mobile number'
            else:
                try:
                    user = User.objects.get(mobile=mobile)
                    OTP.generate(mobile, otp_type="forgot")
                    request.session['forgot_mobile'] = mobile
                    return render(request, 'users/forgot_password.html', {
                        'step': 2, 'mobile': mobile
                    })
                except User.DoesNotExist:
                    error = '❌ No account found with this mobile number'

        # ── Step 2: OTP verify ──
        elif step == '2':
            mobile = request.session.get('forgot_mobile')
            entered_otp = request.POST.get('otp', '').strip()
            try:
                otp_obj = OTP.objects.get(mobile=mobile, otp=entered_otp, is_used=False)
                otp_obj.is_used = True
                otp_obj.save()
                request.session['forgot_verified'] = True
                return render(request, 'users/forgot_password.html', {
                    'step': 3, 'mobile': mobile
                })
            except OTP.DoesNotExist:
                error = '❌ Invalid or expired OTP'
                return render(request, 'users/forgot_password.html', {
                    'step': 2, 'mobile': mobile, 'error': error
                })

        # ── Step 3: New password set ──
        elif step == '3':
            mobile   = request.session.get('forgot_mobile')
            verified = request.session.get('forgot_verified')
            if not verified:
                return redirect('forgot_password')

            new_password     = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()

            if new_password != confirm_password:
                error = '❌ Passwords do not match'
                return render(request, 'users/forgot_password.html', {
                    'step': 3, 'mobile': mobile, 'error': error
                })

            user = User.objects.get(mobile=mobile)
            user.set_password(new_password)
            user.save()

            # ✅ Password Reset Success SMS
            try:
                from users.sms_utils import send_password_reset_success_sms
                send_password_reset_success_sms(mobile, user.username)
                print(f"DEBUG Password Reset SMS: mobile={mobile}")
            except Exception as e:
                print(f"SMS Error: {e}")

            # Clear session
            del request.session['forgot_mobile']
            del request.session['forgot_verified']

            return render(request, 'users/forgot_password.html', {
                'step': 'done'
            })

    return render(request, 'users/forgot_password.html', {'step': 1})



# ← Yeh 3 lines add karo
from django.contrib.auth import get_user_model
from users.models import OTP, CustomUser, RegistrationDraft

User = get_user_model()




def send_otp(request, role):
    error = None

    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()

        if len(mobile) != 10 or not mobile.isdigit():
            error = 'Please enter a valid 10 digit mobile number.'
        else:
            # Check if number already exists
            existing = CustomUser.objects.filter(mobile=mobile).first()
            if existing:
                if existing.role != role:
                    error = f'❌ This number is already registered as {existing.role}. Please login instead.'
                else:
                    error = f'❌ This number is already registered. Please login.'
            else:
                generated_otp = OTP.generate(mobile, otp_type="signup")
                request.session['otp_mobile'] = mobile
                request.session['otp_role']   = role
                return redirect('verify_otp')

    return render(request, 'users/send_otp.html', {
        'role':  role,
        'error': error,
    })


def verify_otp(request):
    from users.models import RegistrationDraft
    mobile = request.session.get('otp_mobile')
    role   = request.session.get('otp_role')
    error  = None

    if not mobile:
        return redirect('home')

    # ← DB se latest OTP nikalo
    latest_otp = OTP.objects.filter(mobile=mobile, is_used=False).order_by('-created_at').first()

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        try:
            otp_obj = OTP.objects.get(mobile=mobile, otp=entered_otp, is_used=False)
            otp_obj.is_used = True
            otp_obj.save()

            is_new = False
            raw_password = None
            try:
                user = CustomUser.objects.get(mobile=mobile)
            except CustomUser.DoesNotExist:
                raw_password = secrets.token_hex(8)
                user = CustomUser.objects.create_user(
                    username=f"{role}_{mobile}",
                    password=raw_password,
                    mobile=mobile,
                    role=role,
                )
                is_new = True

            login(request, user)
            request.session.save()

            request.session['otp_mobile'] = mobile
            request.session['otp_role']   = role

            if is_new:
                request.session['new_credentials'] = {
                    'username': f"{role}_{mobile}",
                    'password': raw_password,
                }
                request.session.save()
                # ✅ Welcome SMS
                try:
                    from users.sms_utils import send_welcome_sms
                    send_welcome_sms(mobile, role.title())
                    print(f"DEBUG Welcome SMS: mobile={mobile}, role={role}")
                except Exception as e:
                    print(f"SMS Error: {e}")

            profile_complete    = False
            verification_status = 'pending'
            try:
                if role == 'doctor':
                    profile = user.doctor_profile
                elif role == 'nurse':
                    profile = user.nurse_profile
                elif role == 'hospital':
                    profile = user.hospital_profile

                profile_complete    = profile.is_registration_complete
                verification_status = profile.verification_status
            except:
                pass

            if profile_complete:
                if verification_status == 'approved':
                    return redirect(f'{role}_dashboard')
                else:
                    return redirect('verification_pending')

            try:
                draft = user.draft
                step_map = {
                    ('doctor',   1): 'doctor_register_step1',
                    ('doctor',   2): 'doctor_register_step2',
                    ('doctor',   3): 'doctor_register_step3',
                    ('nurse',    1): 'nurse_register_step1',
                    ('nurse',    2): 'nurse_register_step2',
                    ('nurse',    3): 'nurse_register_step3',
                    ('hospital', 1): 'hospital_register_step1',
                    ('hospital', 2): 'hospital_register_step2',
                }
                url = step_map.get((draft.role, draft.current_step), f'{role}_register_step1')
                return redirect(url)
            except RegistrationDraft.DoesNotExist:
                return redirect(f'{role}_register_step1')

        except OTP.DoesNotExist:
            error = 'OTP incorrect or expired!'

    return render(request, 'users/verify_otp.html', {
        'mobile':    mobile,
        'error':     error,
        'otp_debug': latest_otp.otp if latest_otp else None,  # ← yeh
    })

import json
from django.http import JsonResponse

@login_required
def send_mobile_otp(request):
    if request.method == 'POST':
        data   = json.loads(request.body)
        mobile = data.get('mobile', '').strip()

        if len(mobile) != 10 or not mobile.isdigit():
            return JsonResponse({'success': False, 'error': 'Invalid mobile number'})

        if User.objects.filter(mobile=mobile).exclude(id=request.user.id).exists():
            return JsonResponse({'success': False, 'error': 'Mobile number already registered'})

        OTP.generate(mobile, otp_type="login")

        request.session['pending_mobile'] = mobile
        return JsonResponse({'success': True, 'message': 'OTP sent! Check console.'})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def verify_mobile_otp(request):
    if request.method == 'POST':
        data        = json.loads(request.body)
        otp_entered = data.get('otp', '').strip()
        mobile      = request.session.get('pending_mobile')

        if not mobile:
            return JsonResponse({'success': False, 'error': 'Session expired, try again'})

        try:
            otp_obj = OTP.objects.filter(mobile=mobile, is_used=False).latest('created_at')
        except OTP.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'OTP not found, resend karo'})

        if otp_obj.otp != otp_entered:
            return JsonResponse({'success': False, 'error': 'Invalid OTP'})

        request.user.mobile = mobile
        request.user.save()
        otp_obj.is_used = True
        otp_obj.save()
        del request.session['pending_mobile']

        return JsonResponse({'success': True, 'message': 'Mobile updated successfully!'})

    return JsonResponse({'success': False, 'error': 'Invalid request'})