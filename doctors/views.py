from plans.utils import get_active_plan
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from doctors.models import DoctorProfile
from django.db.models import Q
from django.utils import timezone

from shifts.views import qualifications_match, location_matches

try:
    from shifts.models import Shift, ShiftApplication
    SHIFTS_ENABLED = True
except ImportError:
    SHIFTS_ENABLED = False


def get_user_profile(user):
    try:
        return user.doctor_profile
    except Exception:
        pass
    try:
        return user.nurse_profile
    except Exception:
        pass
    return None


@login_required
def dashboard(request):
    try:
        profile = request.user.doctor_profile
    except DoctorProfile.DoesNotExist:
        return redirect('doctor_register_step1')

    credentials = request.session.pop('new_credentials', None)

    has_photo   = bool(profile.profile_photo)
    has_degree  = bool(getattr(profile, 'degree_photo', None))
    has_city    = bool(getattr(profile, 'city', None))
    has_qual    = bool(getattr(profile, 'qualification', None))
    is_verified = getattr(profile, 'verification_status', '') == 'approved'

    setup_steps = [
        {'number': 1, 'title': 'Complete your profile', 'desc': 'Add your name, city and qualification', 'done': bool(profile.full_name and has_city and has_qual), 'url': '/doctors/profile/', 'icon': 'user'},
        {'number': 2, 'title': 'Upload your documents', 'desc': 'Profile photo & degree for verification', 'done': has_photo and has_degree, 'url': '/doctors/profile/', 'icon': 'doc'},
        {'number': 3, 'title': 'Get verified', 'desc': 'Admin will review and approve your profile', 'done': is_verified, 'url': '/doctors/profile/', 'icon': 'shield'},
        {'number': 4, 'title': 'Browse available shifts', 'desc': 'Find shifts matching your qualification & city', 'done': False, 'url': '/doctors/shifts/available/', 'icon': 'shift'},
        {'number': 5, 'title': 'Apply for a shift', 'desc': 'Apply and get selected by a hospital', 'done': False, 'url': '/doctors/shifts/applications/', 'icon': 'apply'},
    ]

    # ── Plan check ──────────────────────────────────────────────
    active_plan       = get_active_plan(request.user)
    can_view_shifts   = False
    can_view_urgent   = False
    can_apply_vacancy = False
    can_post_shift    = False

    if active_plan and active_plan.plan:
        p = active_plan.plan
        can_view_shifts   = p.shift_view_enabled
        can_view_urgent   = p.urgent_shift_enabled and p.shift_view_enabled
        can_apply_vacancy = p.vacancy_apply_enabled
        can_post_shift    = p.shift_post_enabled

    context = {
        'profile':          profile,
        'credentials':      credentials,
        'available_count':  0,
        'applied_count':    0,
        'selected_count':   0,
        'posted_count':     0,
        'urgent_shifts':    [],
        'urgent_count':     0,
        'setup_steps':      setup_steps,
        'steps_done':       0,
        'steps_total':      len(setup_steps),
        'show_setup_guide': True,
        'can_view_shifts':   can_view_shifts,
        'can_view_urgent':   can_view_urgent,
        'can_apply_vacancy': can_apply_vacancy,
        'can_post_shift':    can_post_shift,
        'active_plan':       active_plan,
    }

    if SHIFTS_ENABLED:
        today        = timezone.now().date()
        user_role    = getattr(request.user, 'role', 'doctor')
        user_profile = get_user_profile(request.user)

        # ── Raw shifts ───────────────────────────────────────
        raw_shifts = Shift.objects.filter(
            is_active=True
        ).exclude(
            posted_by=request.user
        ).filter(
            Q(target_role=user_role) | Q(target_role='both')
        ).order_by('-is_urgent', '-created_at')

        # ── Expired hatao ────────────────────────────────────
        all_shifts = raw_shifts.filter(start_date__gte=today)

        # ── Qual + Location match ────────────────────────────
        matched_shifts = []
        for shift in all_shifts:
            qual_match, _ = qualifications_match(user_profile, shift)
            loc_match,  _ = location_matches(user_profile, shift)
            if qual_match and loc_match:
                matched_shifts.append(shift)

        # ── Applied IDs ──────────────────────────────────────
        applied_ids = ShiftApplication.objects.filter(
    applicant=request.user,
    status__in=['applied', 'accepted', 'onboard', 'started', 'completed']
).values_list('shift_id', flat=True)

        applied_count = ShiftApplication.objects.filter(
            applicant=request.user
        ).exclude(status='withdrawn').count()

        # ── Urgent shifts — sirf tab jab plan mein allowed ho
        if can_view_urgent:
            urgent_shifts = [
                s for s in matched_shifts
                if getattr(s, 'is_urgent', False) and s.id not in applied_ids
            ][:5]
        else:
            urgent_shifts = []

        context['available_count'] = len(matched_shifts) if can_view_shifts else 0
        context['applied_count']   = applied_count
        context['selected_count']  = ShiftApplication.objects.filter(applicant=request.user, status='accepted').count()
        context['posted_count']    = Shift.objects.filter(posted_by=request.user).count()
        context['urgent_shifts']   = urgent_shifts
        context['urgent_count']    = len(urgent_shifts)

        setup_steps[3]['done'] = len(matched_shifts) > 0 and can_view_shifts
        setup_steps[4]['done'] = applied_count > 0

        steps_done = sum(1 for s in setup_steps if s['done'])
        context['steps_done']       = steps_done
        context['setup_steps']      = setup_steps
        context['show_setup_guide'] = steps_done < len(setup_steps)

    return render(request, 'doctors/dashboard.html', context)


DOCTOR_PROCEDURES = [
    'IM/SC/ID/IV Injection', 'IV Cannulation Peripheral', 'Dressing and Wound Care',
    'Suture', 'Urine Catheterization (Foleys)', 'Central Line IV', 'Intubation',
    'ABG Collection', 'Incision and Drainage', 'Pleural Tapping',
    'Ryles Tube Insertion', 'CPR', 'ECG Basic Interpretation',
    'ECG Recording', 'Vitals Monitoring (BP/Pulse/HGT)', 'Blood Collection',
]

WARD_CHOICES_DOCTOR = [
    ('general', 'General Ward'),
    ('icu', 'ICU Ward'),
    ('casualty', 'Casualty Ward'),
    ('female', 'Female Ward'),
]

@login_required
def my_profile(request):
    profile = request.user.doctor_profile
    user    = request.user
    success = None
    error   = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile.full_name        = request.POST.get('full_name', profile.full_name)
            profile.age              = request.POST.get('age') or profile.age
            profile.sex              = request.POST.get('sex', profile.sex)
            profile.experience       = request.POST.get('experience', profile.experience)
            profile.address          = request.POST.get('address', profile.address)
            profile.city             = request.POST.get('city', profile.city)
            profile.state            = request.POST.get('state', profile.state)
            profile.pincode          = request.POST.get('pincode', profile.pincode)
            profile.ward_preferences = request.POST.get('ward_preferences', profile.ward_preferences)
            profile.known_procedures = request.POST.get('known_procedures', profile.known_procedures)
            profile.upi_id = request.POST.get('upi_id', profile.upi_id)

            if 'profile_photo' in request.FILES:
                profile.profile_photo = request.FILES['profile_photo']
            if 'degree_photo' in request.FILES:
                profile.degree_photo = request.FILES['degree_photo']
            if 'aadhar_photo' in request.FILES:
                profile.aadhar_photo = request.FILES['aadhar_photo']
            if 'pan_card' in request.FILES:
                profile.pan_card = request.FILES['pan_card']
            profile.save()
            success = 'Profile updated successfully'

        elif action == 'update_photo':
            if 'profile_photo' in request.FILES:
                profile.profile_photo = request.FILES['profile_photo']
                profile.save()
                success = 'Profile photo updated successfully!'

        elif action == 'update_procedures':
            profile.known_procedures = ','.join(request.POST.getlist('procedures'))
            profile.save()
            success = 'Procedures updated successfully'

        elif action == 'update_ward_preferences':
            profile.ward_preferences = ','.join(request.POST.getlist('ward_preferences'))
            profile.save()
            success = 'Ward preferences updated successfully!'

        elif action == 'change_password':
            old_pass = request.POST.get('old_password')
            new_pass = request.POST.get('new_password')
            confirm  = request.POST.get('confirm_password')
            if not user.check_password(old_pass):
                error = 'Old password is incorrect'
            elif new_pass != confirm:
                error = 'New password does not match'
            elif len(new_pass) < 6:
                error = 'Password must be at least 6 characters long'
            else:
                user.set_password(new_pass)
                user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                try:
                    from users.sms_utils import send_password_reset_success_sms
                    send_password_reset_success_sms(user.mobile, user.username)
                except Exception as e:
                    print(f"SMS Error: {e}")
                success = 'Password changed successfully'

        elif action == 'change_username':
            new_username = request.POST.get('new_username', '').strip()
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                error = 'This username is already taken'
            elif len(new_username) < 4:
                error = 'Username must be at least 4 characters long'
            else:
                user.username = new_username
                user.save()
                success = 'Username changed successfully!'

    selected_procedures = profile.known_procedures.split(',') if profile.known_procedures else []
    selected_wards      = profile.ward_preferences.split(',') if profile.ward_preferences else []

    return render(request, 'doctors/my_profile.html', {
        'profile':             profile,
        'user':                user,
        'success':             success,
        'error':               error,
        'procedures_list':     DOCTOR_PROCEDURES,
        'selected_procedures': selected_procedures,
        'ward_choices':        WARD_CHOICES_DOCTOR,
        'selected_wards':      selected_wards,
    })




@login_required
def my_wallet(request):
    from plans.models import Wallet, WalletTransaction
    try:
        wallet = request.user.wallet
        wallet_balance      = wallet.balance
        wallet_transactions = wallet.transactions.order_by('-created_at')
    except:
        wallet_balance      = 0
        wallet_transactions = []

    return render(request, 'doctors/wallet.html', {
        'wallet_balance':      wallet_balance,
        'wallet_transactions': wallet_transactions,
        'user':                request.user,
    })