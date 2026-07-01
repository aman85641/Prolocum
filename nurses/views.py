from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from nurses.models import NurseProfile
from plans.utils import get_active_plan

try:
    from shifts.models import Shift, ShiftApplication
    SHIFTS_ENABLED = True
except ImportError:
    SHIFTS_ENABLED = False


def get_nurse_profile(user):
    try:
        return user.nurse_profile
    except Exception:
        return None


@login_required
def dashboard(request):
    try:
        profile = request.user.nurse_profile
    except NurseProfile.DoesNotExist:
        return redirect('nurse_register_step1')

    credentials = request.session.pop('new_credentials', None)

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
        'can_view_shifts':   can_view_shifts,
        'can_view_urgent':   can_view_urgent,
        'can_apply_vacancy': can_apply_vacancy,
        'can_post_shift':    can_post_shift,
        'active_plan':       active_plan,
    }

    if SHIFTS_ENABLED:
        today        = timezone.now().date()
        user_profile = get_nurse_profile(request.user)

        raw_shifts = Shift.objects.filter(
            is_active=True
        ).exclude(
            posted_by=request.user
        ).filter(
            Q(target_role='nurse') | Q(target_role='both')
        ).order_by('-is_urgent', '-created_at')

        all_shifts = raw_shifts.filter(start_date__gte=today)

        # Qual + Location match
        from shifts.views import qualifications_match, location_matches
        matched_shifts = []
        for shift in all_shifts:
            qual_match, _ = qualifications_match(user_profile, shift)
            loc_match,  _ = location_matches(user_profile, shift)
            if qual_match and loc_match:
                matched_shifts.append(shift)

        applied_ids = ShiftApplication.objects.filter(
    applicant=request.user,
    status__in=['applied', 'accepted', 'onboard', 'started', 'completed']
).values_list('shift_id', flat=True)
        applied_count = ShiftApplication.objects.filter(
            applicant=request.user
        ).exclude(status='withdrawn').count()

        # Urgent shifts — sirf plan mein allow ho tab
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

    return render(request, 'nurses/dashboard.html', context)

from shifts.views import get_user_profile, qualifications_match, location_matches


# ─── Available Shifts ─────────────────────────────────────────
# ─── Available Shifts ─────────────────────────────────────────
@login_required
def available_shifts(request):
    today = timezone.now().date()

    applied_ids = ShiftApplication.objects.filter(
        applicant=request.user,
        status__in=['applied', 'accepted', 'reserved']
    ).values_list('shift_id', flat=True)

    all_shifts = Shift.objects.filter(
        is_active=True,
        start_date__gte=today
    ).exclude(
        posted_by=request.user
    ).exclude(
        id__in=applied_ids
    ).filter(
        Q(target_role='nurse') | Q(target_role='both')
    ).order_by('-is_urgent', '-created_at')

    user_profile = get_user_profile(request.user)

    matched_shifts = []
    for shift in all_shifts:
        loc_match, _ = location_matches(user_profile, shift)
        if loc_match:
            matched_shifts.append(shift)

    return render(request, 'doctors/available_shifts.html', {
        'shifts': matched_shifts,
        'applied_ids': list(applied_ids),
        'base_template': 'nurses/base.html',
        'detail_url_name': 'nurse_shift_detail',
    })

# ─── Shift Detail + Apply ─────────────────────────────────────
@login_required
def shift_detail(request, shift_id):
    from shifts.views import get_role_config
    from plans.utils import get_wallet_balance

    cfg   = get_role_config(request.user)
    shift = get_object_or_404(Shift, id=shift_id, is_active=True)

    shift_expired   = shift.start_date < timezone.now().date()
    already_applied = ShiftApplication.objects.filter(
        shift=shift, applicant=request.user
    ).first()

    wallet_balance = get_wallet_balance(request.user)
    token_cost     = getattr(shift, 'pay', 0)

    can_apply = (
        not shift_expired   and
        not already_applied and
        wallet_balance >= token_cost
    )

    if request.method == 'POST':
        if shift_expired:
            messages.error(request, '❌ This shift date has already passed, you cannot apply.')
        elif already_applied:
            messages.warning(request, 'You have already applied for this shift.')
        elif wallet_balance < token_cost:
            messages.error(
                request,
                f'❌ Insufficient tokens. This shift requires {token_cost} tokens, '
                f'but you only have {wallet_balance}.'
            )
        else:
            ShiftApplication.objects.create(shift=shift, applicant=request.user)
            messages.success(request, '✅ Application submitted successfully!')
            return redirect(cfg['success_url'], shift_id=shift.id)

    return render(request, 'doctors/shift_detail.html', {
        'shift':           shift,
        'already_applied': already_applied,
        'shift_expired':   shift_expired,
        'base_template':   cfg['base'],
        'can_apply':       can_apply,
        'wallet_balance':  wallet_balance,
        'token_cost':      token_cost,
    })


# ─── Applied Success ──────────────────────────────────────────
@login_required
def shift_applied_success(request, shift_id):
    from shifts.views import get_role_config
    cfg         = get_role_config(request.user)
    shift       = get_object_or_404(Shift, id=shift_id)
    application = get_object_or_404(ShiftApplication, shift=shift, applicant=request.user)

    return render(request, 'doctors/shift_applied_success.html', {
        'shift':            shift,
        'application':      application,
        'base_template':    cfg['base'],
        'applications_url': cfg['applications_url'],
        'withdraw_url':     cfg['withdraw_url'],
    })


@login_required
def post_new_shift(request):
    from shifts.forms import ShiftForm
    from plans.utils import can_post_shift, deduct_shift_post_token, get_active_plan

    if request.method == 'POST':
        can_post, msg = can_post_shift(request.user)
        if not can_post:
            messages.error(request, f'❌ {msg}')
            return redirect('nurse_posted_shifts')

        form = ShiftForm(request.POST)
        if form.is_valid():
            shift = form.save(commit=False)
            shift.posted_by = request.user

            # ✅ Urgent permission check
            if shift.is_urgent:
                user_plan = get_active_plan(request.user)
                if not user_plan or not user_plan.plan.urgent_shift_post_enabled:
                    shift.is_urgent = False

            token_cost = shift.pay or 0
            if token_cost > 0:
                success, token_msg = deduct_shift_post_token(request.user, cost=token_cost)
                if not success:
                    messages.error(request, f'❌ {token_msg}')
                    user_plan = get_active_plan(request.user)
                    can_post_urgent = bool(user_plan and user_plan.plan.urgent_shift_post_enabled)
                    return render(request, 'doctors/post_new_shift.html', {
                        'form':            form,
                        'base_template':   'nurses/base.html',
                        'cancel_url':      'nurse_posted_shifts',
                        'default_role':    'nurse',
                        'role_locked':     True,
                        'can_post_urgent': can_post_urgent,
                    })

            shift.save()

            try:
                from users.sms_utils import send_new_shift_sms, send_emergency_broadcast_sms
                from users.models import CustomUser
                from shifts.views import qualifications_match, location_matches

                target_role = shift.target_role
                if target_role == 'both':
                    users = CustomUser.objects.filter(
                        role__in=['doctor', 'nurse'], mobile__isnull=False
                    ).exclude(id=request.user.id)
                else:
                    users = CustomUser.objects.filter(
                        role=target_role, mobile__isnull=False
                    ).exclude(id=request.user.id)

                matched_users = []
                for u in users:
                    try:
                        if u.role == 'doctor':
                            user_profile = u.doctor_profile
                        elif u.role == 'nurse':
                            user_profile = u.nurse_profile
                        else:
                            continue
                    except:
                        continue

                    qual_match, _ = qualifications_match(user_profile, shift)
                    loc_match, _  = location_matches(user_profile, shift)

                    if qual_match and loc_match:
                        matched_users.append(u)

                for u in matched_users:
                    send_new_shift_sms(
                        mobile   = u.mobile,
                        name     = u.username,
                        position = shift.hospital_name,
                        location = getattr(shift, 'city', '') or getattr(shift, 'location', ''),
                        date     = str(shift.start_date),
                    )
                print(f"DEBUG New Shift SMS sent to {len(matched_users)} matched users")

                if getattr(shift, 'is_urgent', False):
                    for u in matched_users:
                        send_emergency_broadcast_sms(
                            mobile     = u.mobile,
                            role       = target_role if target_role != 'both' else 'Doctor/Nurse',
                            location   = getattr(shift, 'city', '') or getattr(shift, 'location', ''),
                            shift_time = f"{shift.start_time} - {shift.end_time}",
                        )
                    print(f"DEBUG Emergency SMS sent to {len(matched_users)} matched users")

            except Exception as e:
                print(f"SMS Error: {e}")

            messages.success(request, '✅ Shift posted successfully!')
            return redirect('nurse_posted_shifts')
    else:
        form = ShiftForm(initial={'target_role': 'nurse'})

    user_plan = get_active_plan(request.user)
    can_post_urgent = bool(user_plan and user_plan.plan.urgent_shift_post_enabled)

    return render(request, 'doctors/post_new_shift.html', {
        'form':            form,
        'base_template':   'nurses/base.html',
        'cancel_url':      'nurse_posted_shifts',
        'default_role':    'nurse',
        'role_locked':     True,
        'can_post_urgent': can_post_urgent,
    })

@login_required
def posted_shifts(request):
    from shifts.views import get_role_config
    cfg = get_role_config(request.user)
    shifts = Shift.objects.filter(
        posted_by=request.user
    ).order_by('-created_at')

    return render(request, 'doctors/posted_shifts.html', {
        'shifts': shifts,
        'base_template': cfg['base'],
        'post_url': cfg['post_url'],
        'deactivate_url': cfg['deactivate_url'],
        'applicants_url': 'shift_applicants',
    })


# ─── My Applications ──────────────────────────────────────────
@login_required
def my_applications(request):
    from itertools import chain

    all_apps = ShiftApplication.objects.filter(
        applicant=request.user
    ).select_related('shift').order_by('-applied_at')

    applied_apps   = all_apps.filter(status__in=['applied', 'reserved', 'rejected'])
    withdrawn_apps = all_apps.filter(status='withdrawn')
    accepted_apps  = all_apps.filter(status='accepted', onboard_status__in=['pending'])
    onboard_apps   = all_apps.filter(status='accepted', onboard_status__in=['onboarded', 'arrived', 'started'])
    completed_apps = all_apps.filter(status='accepted', onboard_status='completed')

    # ← ADD KARO
    for app in onboard_apps:
        can, _ = app.can_withdraw()
        app.can_withdraw_status = can

    completed_with_reviews = []
    for app in completed_apps:
        my_review       = app.reviews.filter(reviewer_type='doctor').first()
        hospital_review = app.reviews.filter(reviewer_type='hospital').first()
        completed_with_reviews.append({
            'app':             app,
            'my_review':       my_review,
            'hospital_review': hospital_review,
        })

    all_applied = list(chain(applied_apps, accepted_apps))
    all_applied.sort(key=lambda x: x.applied_at, reverse=True)

    return render(request, 'doctors/my_applications.html', {
        'applied_apps':           all_applied,
        'withdrawn_apps':         withdrawn_apps,
        'onboard_apps':           onboard_apps,
        'completed_apps':         completed_apps,
        'completed_with_reviews': completed_with_reviews,
        'base_template':          'nurses/base.html',
        'withdraw_url':           'nurse_withdraw_application',
        'available_url':          'nurse_available_shifts',
        'review_url':             'submit_review',
        'detail_url_name':        'nurse_shift_detail',
    })

# ─── Withdraw Application ─────────────────────────────────────
@login_required
def withdraw_application(request, app_id):
    application = get_object_or_404(ShiftApplication, id=app_id, applicant=request.user)

    if application.status in ['applied', 'reserved']:
        application.status = 'withdrawn'
        application.save()
        messages.success(request, '✅ Application withdrawn successfully.')

    elif application.status == 'accepted':
        can, reason = application.can_withdraw()
        if can:
            from plans.models import Wallet, WalletTransaction
            try:
                wallet = application.applicant.wallet
                refund_amount = application.shift.pay
                wallet.balance += refund_amount
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type='credit',
                    description=f'Refund: Withdrawn from {application.shift.hospital_name} shift'
                )
            except Exception as e:
                messages.error(request, f'❌ Refund failed: {e}')
                return redirect('nurse_my_applications')

            application.status = 'withdrawn'
            application.save()
            messages.success(request, f'✅ Withdrawn successfully. ₹{application.shift.pay} tokens refunded!')
        else:
            messages.warning(request, f'⚠ {reason}')
    else:
        messages.warning(request, '⚠ This application cannot be withdrawn.')

    return redirect('nurse_my_applications')


# ─── Deactivate Shift ─────────────────────────────────────────
@login_required
def deactivate_shift(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)
    shift.is_active = False
    shift.save()
    messages.success(request, 'Shift deactivated successfully.')
    return redirect('nurse_posted_shifts')

NURSE_PROCEDURES = [
    'IM/SC/ID/IV Injection', 'IV Cannulation Peripheral', 'Dressing and Wound Care',
    'Urine Catheterization (Foleys)', 'Ryles Tube Insertion', 'CPR',
    'ECG Recording', 'Vitals Monitoring (BP/Pulse/HGT)', 'Blood Collection',
    'Oxygen Administration', 'Nebulization', 'Suctioning',
    'Tracheostomy Care', 'Colostomy Care', 'Bed Bath & Patient Hygiene',
]


WARD_CHOICES_NURSE = [
    ('general', 'General Ward'),
    ('icu', 'ICU Ward'),
    ('casualty', 'Casualty Ward'),
    ('female', 'Female Ward'),
    ('pediatric', 'Pediatric Ward'),
    ('maternity', 'Maternity Ward'),
]

@login_required
def my_profile(request):
    profile = request.user.nurse_profile
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
            success = 'Profile updated successfully!'

        elif action == 'update_photo':
            if 'profile_photo' in request.FILES:
                profile.profile_photo = request.FILES['profile_photo']
                profile.save()
                success = 'Profile photo updated successfully!'

        elif action == 'update_procedures':
            profile.known_procedures = ','.join(request.POST.getlist('procedures'))
            profile.save()
            success = 'Skills updated successfully!'

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
                success = 'Password changed successfully!'

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

    return render(request, 'nurses/my_profile.html', {
        'profile':             profile,
        'user':                user,
        'success':             success,
        'error':               error,
        'procedures_list':     NURSE_PROCEDURES,
        'selected_procedures': selected_procedures,
        'ward_choices':        WARD_CHOICES_NURSE,
        'selected_wards':      selected_wards,
    })



@login_required
def edit_shift(request, shift_id):
    from shifts.forms import ShiftForm
    from shifts.models import Shift
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)

    if request.method == 'POST':
        form = ShiftForm(request.POST, instance=shift)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Shift updated successfully!')
            return redirect('nurse_posted_shifts')
    else:
        form = ShiftForm(instance=shift)

    return render(request, 'doctors/post_new_shift.html', {
        'form':          form,
        'base_template': 'nurses/base.html',
        'cancel_url':    'nurse_posted_shifts',
        'default_role':  'nurse',
        'role_locked':   True,
        'edit_mode':     True,
        'shift':         shift,
    })


@login_required
def delete_shift(request, shift_id):
    from shifts.models import Shift
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)
    if request.method == 'POST':
        shift.delete()
        messages.success(request, '✅ Shift deleted successfully!')
    return redirect('nurse_posted_shifts')


@login_required
def my_wallet(request):
    from plans.models import Wallet
    try:
        wallet = request.user.wallet
        wallet_balance      = wallet.balance
        wallet_transactions = wallet.transactions.order_by('-created_at')
    except:
        wallet_balance      = 0
        wallet_transactions = []

    return render(request, 'nurses/wallet.html', {
        'wallet_balance':      wallet_balance,
        'wallet_transactions': wallet_transactions,
        'user':                request.user,
    })