from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .models import Shift, ShiftApplication, ShiftReview
from .forms import ShiftForm, ReviewForm
from plans.utils import deduct_shift_token


# ─── Role config ─────────────────────────────────────────────
def get_role_config(user):
    role = getattr(user, 'role', 'doctor')
    config = {
        'doctor': {
            'base': 'doctors/base.html',
            'detail_url': 'shift_detail',
            'success_url': 'shift_applied_success',
            'posted_url': 'posted_shifts',
            'applications_url': 'my_applications',
            'withdraw_url': 'withdraw_application',
            'deactivate_url': 'deactivate_shift',
            'post_url': 'post_new_shift',
            'available_url': 'available_shifts',
            'review_url': 'submit_review',
        },
        'nurse': {
            'base': 'nurses/base.html',
            'detail_url': 'nurse_shift_detail',
            'success_url': 'nurse_shift_success',
            'posted_url': 'nurse_posted_shifts',
            'applications_url': 'nurse_my_applications',
            'withdraw_url': 'nurse_withdraw_application',
            'deactivate_url': 'nurse_deactivate_shift',
            'post_url': 'nurse_post_shift',
            'available_url': 'nurse_available_shifts',
            'review_url': 'submit_review',
        },
        'hospital': {
            'base': 'hospitals/base.html',
            'detail_url': 'shift_detail',
            'success_url': 'shift_applied_success',
            'posted_url': 'posted_shifts',
            'applications_url': 'my_applications',
            'withdraw_url': 'withdraw_application',
            'deactivate_url': 'deactivate_shift',
            'post_url': 'post_new_shift',
            'available_url': 'available_shifts',
            'review_url': 'submit_hospital_review',
        },
    }
    return config.get(role, config['doctor'])


# ─── Helper: User profile fetch ──────────────────────────────
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


# ─── Helper: Qualification match check ───────────────────────
def qualifications_match(user_profile, shift):
    shift_qual = getattr(shift, 'qualification_required', None)

    debug = {
        'user_qualification': None,
        'shift_qualification_required': shift_qual,
        'match': False,
        'reason': '',
    }

    if user_profile is None:
        debug['reason'] = 'User profile not found, filter skipped'
        debug['match'] = True
        return True, debug

    user_qual = getattr(user_profile, 'qualification', None)
    debug['user_qualification'] = user_qual

    if not shift_qual:
        debug['reason'] = 'Shift qualification_required blank, open for all'
        debug['match'] = True
        return True, debug

    if not user_qual:
        debug['reason'] = 'User qualification blank, filter skipped'
        debug['match'] = True
        return True, debug

    if shift_qual == 'bams_bhms' and user_qual in ('bams', 'bhms'):
        debug['match'] = True
        debug['reason'] = f'bams_bhms group match: user={user_qual}'
        return True, debug

    matched = user_qual.strip().lower() == shift_qual.strip().lower()
    debug['match'] = matched
    debug['reason'] = 'Qualification match ✅' if matched else f'Mismatch ❌: user={user_qual}, shift={shift_qual}'
    return matched, debug


# ─── Helper: Location match check ────────────────────────────
def location_matches(user_profile, shift):
    debug = {
        'user_location': None,
        'shift_location': getattr(shift, 'location', None),
        'match': False,
        'reason': '',
    }

    if user_profile is None:
        debug['reason'] = 'User profile not found, location match skipped'
        debug['match'] = True
        return True, debug

    shift_city = getattr(shift, 'city', None)
    user_city  = getattr(user_profile, 'city', None) or getattr(user_profile, 'location', None)

    debug['user_location']  = user_city
    debug['shift_location'] = shift_city

    if not shift_city:
        debug['reason'] = 'Shift city blank, open for all'
        debug['match'] = True
        return True, debug

    if not user_city:
        debug['reason'] = 'User city blank, filter skipped'
        debug['match'] = True
        return True, debug

    matched = user_city.strip().lower() == shift_city.strip().lower()
    debug['match'] = matched
    debug['reason'] = 'City match ✅' if matched else f'Mismatch ❌: user={user_city}, shift={shift_city}'
    return matched, debug


# ─── Helper: Shift conflict check ────────────────────────────
def has_shift_conflict(applicant, new_shift):
    """
    Check if applicant already has an accepted shift
    that overlaps with new_shift on the same date and time.
    Returns (True, conflicting_shift) or (False, None)
    """
    existing_accepted = ShiftApplication.objects.filter(
        applicant=applicant,
        status='accepted',
    ).exclude(shift=new_shift).select_related('shift')

    new_date  = new_shift.start_date
    new_start = new_shift.start_time
    new_end   = new_shift.end_time

    for app in existing_accepted:
        s = app.shift
        # Same date check
        if s.start_date != new_date:
            continue
        # Time overlap: (A_start < B_end) AND (A_end > B_start)
        if s.start_time < new_end and s.end_time > new_start:
            return True, s

    return False, None


# ─── Available Shifts ─────────────────────────────────────────
@login_required
def available_shifts(request):
    cfg       = get_role_config(request.user)
    user_role = getattr(request.user, 'role', 'doctor')
    today     = timezone.now().date()

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
        Q(target_role=user_role) | Q(target_role='both')
    ).order_by('-is_urgent', '-created_at')

    user_profile = get_user_profile(request.user)

    matched_shifts = []
    for shift in all_shifts:
        qual_match, _ = qualifications_match(user_profile, shift)
        loc_match,  _ = location_matches(user_profile, shift)
        if qual_match and loc_match:
            matched_shifts.append(shift)

    return render(request, 'doctors/available_shifts.html', {
        'shifts':          matched_shifts,
        'applied_ids':     list(applied_ids),
        'base_template':   cfg['base'],
        'detail_url_name': cfg['detail_url'],
    })



@login_required
def shift_detail(request, shift_id):
    cfg   = get_role_config(request.user)
    shift = get_object_or_404(Shift, id=shift_id, is_active=True)

    from plans.utils import get_wallet_balance

    shift_expired = shift.start_date < timezone.now().date()

    already_applied = ShiftApplication.objects.filter(
        shift=shift, applicant=request.user
    ).first()

    wallet_balance = get_wallet_balance(request.user)
    token_cost     = getattr(shift, 'pay', 0)

    can_withdraw = False
    if already_applied:
        can_withdraw, _ = already_applied.can_withdraw()

    can_apply = (
        not shift_expired   and
        not already_applied and
        wallet_balance >= token_cost
    )

    print("\n" + "="*60)
    print(f"[SHIFT DETAIL] User: {request.user} ({request.user.role}) | Shift: #{shift.id}")
    print(f"[SHIFT DETAIL] Shift start_date: {shift.start_date} | Today: {timezone.now().date()}")
    print(f"[SHIFT DETAIL] Shift expired: {shift_expired}")
    print(f"[SHIFT DETAIL] Wallet Balance: {wallet_balance} | Token Cost: {token_cost}")
    print(f"[SHIFT DETAIL] Already Applied: {already_applied}")
    print(f"[SHIFT DETAIL] Can Apply: {can_apply}")
    print(f"[SHIFT DETAIL] Can Withdraw: {can_withdraw}")
    print("="*60 + "\n")

    if request.method == 'POST':
        action = request.POST.get('action', 'apply')

        if action == 'reapply' and already_applied and already_applied.status == 'withdrawn':
            if shift_expired:
                messages.error(request, '❌ Shift date has passed, cannot re-apply.')
            elif wallet_balance < token_cost:
                messages.error(request, f'❌ Insufficient tokens. Need {token_cost}, have {wallet_balance}.')
            else:
                already_applied.status = 'applied'
                already_applied.accepted_at = None
                already_applied.onboard_status = 'pending'
                already_applied.applied_at = timezone.now()
                already_applied.save()
                # ✅ Application Submitted SMS
                try:
                    from users.sms_utils import send_application_submitted_sms
                    mobile = request.user.mobile
                    name   = getattr(get_user_profile(request.user), 'full_name', None) or request.user.username
                    if mobile:
                        send_application_submitted_sms(mobile, name, shift.hospital_name)
                        print(f"DEBUG App Submitted SMS (reapply): mobile={mobile}")
                except Exception as e:
                    print(f"SMS Error: {e}")
                messages.success(request, '✅ Re-applied successfully!')
                return redirect(cfg['success_url'], shift_id=shift.id)

        elif shift_expired:
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
            # ✅ Application Submitted SMS
            try:
                from users.sms_utils import send_application_submitted_sms
                mobile = request.user.mobile
                name   = getattr(get_user_profile(request.user), 'full_name', None) or request.user.username
                if mobile:
                    send_application_submitted_sms(mobile, name, shift.hospital_name)
                    print(f"DEBUG App Submitted SMS: mobile={mobile}, shift={shift.hospital_name}")
            except Exception as e:
                print(f"SMS Error: {e}")
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
        'can_withdraw':    can_withdraw,
    })


# ─── Applied Success ──────────────────────────────────────────
@login_required
def shift_applied_success(request, shift_id):
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
    from plans.utils import can_post_shift, use_shift_post_limit, deduct_shift_post_token, get_active_plan
    cfg = get_role_config(request.user)
    user_role = request.user.role

    if user_role == 'hospital':
        default_role = 'both'
        role_locked  = False
    elif user_role == 'nurse':
        default_role = 'nurse'
        role_locked  = True
    else:
        default_role = 'doctor'
        role_locked  = True

    if request.method == 'POST':
        can_post, msg = can_post_shift(request.user)
        if not can_post:
            messages.error(request, f'❌ {msg}')
            return redirect(cfg['posted_url'])

        form = ShiftForm(request.POST)
        if form.is_valid():
            shift = form.save(commit=False)
            shift.posted_by = request.user

            # ✅ Urgent permission check — ab sab roles (hospital/doctor/nurse) ke liye plan se
            if shift.is_urgent:
                user_plan = get_active_plan(request.user)
                if not user_plan or not user_plan.plan.urgent_shift_post_enabled:
                    shift.is_urgent = False

            if user_role in ['doctor', 'nurse']:
                token_cost = shift.pay or 0
                if token_cost > 0:
                    success, token_msg = deduct_shift_post_token(request.user, cost=token_cost)
                    if not success:
                        messages.error(request, f'❌ {token_msg}')
                        user_plan = get_active_plan(request.user)
                        can_post_urgent = bool(user_plan and user_plan.plan.urgent_shift_post_enabled)
                        return render(request, 'doctors/post_new_shift.html', {
                            'form':            form,
                            'base_template':   cfg['base'],
                            'cancel_url':      cfg['posted_url'],
                            'default_role':    default_role,
                            'role_locked':     role_locked,
                            'can_post_urgent': can_post_urgent,
                        })

            shift.save()

            if user_role == 'hospital':
                use_shift_post_limit(request.user)

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
            return redirect(cfg['posted_url'])
    else:
        form = ShiftForm(initial={'target_role': default_role})

    # ✅ can_post_urgent calculate karo — ab sab roles ke liye plan se hi
    user_plan = get_active_plan(request.user)
    can_post_urgent = bool(user_plan and user_plan.plan.urgent_shift_post_enabled)

    return render(request, 'doctors/post_new_shift.html', {
        'form':            form,
        'base_template':   cfg['base'],
        'cancel_url':      cfg['posted_url'],
        'default_role':    default_role,
        'role_locked':     role_locked,
        'can_post_urgent': can_post_urgent,
    })


# ─── Edit Shift ───────────────────────────────────────────────
@login_required
def edit_shift(request, shift_id):
    cfg   = get_role_config(request.user)
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)

    user_role = request.user.role
    if user_role == 'hospital':
        default_role = 'both'
        role_locked  = False
    elif user_role == 'nurse':
        default_role = 'nurse'
        role_locked  = True
    else:
        default_role = 'doctor'
        role_locked  = True

    if request.method == 'POST':
        form = ShiftForm(request.POST, instance=shift)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Shift updated successfully!')
            return redirect(cfg['posted_url'])
    else:
        form = ShiftForm(instance=shift)

    return render(request, 'doctors/post_new_shift.html', {
        'form':          form,
        'base_template': cfg['base'],
        'cancel_url':    cfg['posted_url'],
        'default_role':  default_role,
        'role_locked':   role_locked,
        'edit_mode':     True,
        'shift':         shift,
    })


# ─── Delete Shift ─────────────────────────────────────────────
@login_required
def delete_shift(request, shift_id):
    cfg   = get_role_config(request.user)
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)
    if request.method == 'POST':
        shift.delete()
        messages.success(request, '✅ Shift deleted successfully!')
    return redirect(cfg['posted_url'])


# ─── Posted Shifts ────────────────────────────────────────────
@login_required
def posted_shifts(request):
    cfg    = get_role_config(request.user)
    shifts = Shift.objects.filter(
        posted_by=request.user
    ).order_by('-created_at')

    return render(request, 'doctors/posted_shifts.html', {
        'shifts':         shifts,
        'base_template':  cfg['base'],
        'post_url':       cfg['post_url'],
        'deactivate_url': cfg['deactivate_url'],
    })


# ─── My Applications ──────────────────────────────────────────
@login_required
def my_applications(request):
    cfg = get_role_config(request.user)

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

    from itertools import chain
    all_applied = list(chain(applied_apps, accepted_apps))
    all_applied.sort(key=lambda x: x.applied_at, reverse=True)

    return render(request, 'doctors/my_applications.html', {
        'applied_apps':           all_applied,
        'withdrawn_apps':         withdrawn_apps,
        'onboard_apps':           onboard_apps,
        'completed_apps':         completed_apps,
        'completed_with_reviews': completed_with_reviews,
        'base_template':          cfg['base'],
        'withdraw_url':           cfg['withdraw_url'],
        'available_url':          cfg['available_url'],
        'review_url':             cfg.get('review_url', 'submit_review'),
        'detail_url_name':        cfg['detail_url'],
    })
# ─── Withdraw Application ─────────────────────────────────────
@login_required
def withdraw_application(request, app_id):
    cfg = get_role_config(request.user)
    application = get_object_or_404(ShiftApplication, id=app_id, applicant=request.user)

    if application.status in ['applied', 'reserved']:
        # Applied/Reserved → seedha withdraw, token refund nahi (tokens abhi kate nahi the)
        application.status = 'withdrawn'
        application.save()
        messages.success(request, '✅ Application withdrawn successfully.')

    elif application.status == 'accepted':
        can, reason = application.can_withdraw()
        if can:
            # ── Token Refund ──────────────────────────────
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
                return redirect(cfg['applications_url'])
            # ─────────────────────────────────────────────

            application.status = 'withdrawn'
            application.save()
            messages.success(request, f'✅ Withdrawn successfully. ₹{application.shift.pay} tokens refunded to your wallet.')
        else:
            messages.warning(request, f'⚠ {reason}')
    else:
        messages.warning(request, '⚠ This application cannot be withdrawn.')

    return redirect(cfg['applications_url'])

# ─── Deactivate Shift ─────────────────────────────────────────
@login_required
def deactivate_shift(request, shift_id):
    cfg   = get_role_config(request.user)
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)
    shift.is_active = False
    shift.save()
    messages.success(request, '✅ Shift deactivated successfully.')
    return redirect(cfg['posted_url'])


# ─── Shift Applicants (poster view) ──────────────────────────
@login_required
def shift_applicants(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)

    applications = shift.applications.select_related(
        'applicant'
    ).order_by('-applied_at')

    applicants_data = []
    for app in applications:
        profile = None
        try:
            profile = app.applicant.doctor_profile
        except Exception:
            try:
                profile = app.applicant.nurse_profile
            except Exception:
                pass

        hospital_reviewed = app.reviews.filter(reviewer_type='hospital').exists()
        applicants_data.append({
            'application':       app,
            'profile':           profile,
            'hospital_reviewed': hospital_reviewed,
        })

    cfg = get_role_config(request.user)

    return render(request, 'doctors/shift_applicants.html', {
        'shift':           shift,
        'applicants_data': applicants_data,
        'base_template':   cfg['base'],
    })


@login_required
def update_application_status(request, app_id):
    application = get_object_or_404(
        ShiftApplication,
        id=app_id,
        shift__posted_by=request.user
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status in ['accepted', 'reserved', 'rejected']:

            if new_status == 'accepted':
                conflict, conflict_shift = has_shift_conflict(
                    applicant=application.applicant,
                    new_shift=application.shift,
                )
                if conflict:
                    messages.error(
                        request,
                        f'❌ This applicant is already accepted in another shift on '
                        f'{conflict_shift.start_date} from '
                        f'{conflict_shift.start_time.strftime("%I:%M %p")} - '
                        f'{conflict_shift.end_time.strftime("%I:%M %p")} '
                        f'at {conflict_shift.hospital_name}. '
                        f'Cannot work at 2 places at the same time!'
                    )
                    return redirect('shift_applicants', shift_id=application.shift.id)

                token_cost = application.shift.pay
                success, msg = deduct_shift_token(
                    user=application.applicant,
                    shift=application.shift,
                    token_cost=token_cost,
                )
                if not success:
                    messages.error(request, f'❌ Applicant does not have enough tokens: {msg}')
                    return redirect('shift_applicants', shift_id=application.shift.id)

                application.onboard_status = 'onboarded'
                application.accepted_at = timezone.now()

            application.status = new_status
            application.save()

            # ✅ SMS bhejo
            try:
                from users.sms_utils import (
                    send_application_not_selected_sms,
                    send_shift_confirmation_sms,
                )
                mobile  = application.applicant.mobile
                profile = None
                try:
                    profile = application.applicant.doctor_profile
                except:
                    try:
                        profile = application.applicant.nurse_profile
                    except:
                        pass
                name       = getattr(profile, 'full_name', None) or application.applicant.username
                shift_name = application.shift.hospital_name

                if mobile:
                    if new_status == 'accepted':
                        send_shift_confirmation_sms(
                            mobile   = mobile,
                            name     = name,
                            hospital = application.shift.hospital_name,
                            date     = str(application.shift.start_date),
                            time     = str(application.shift.start_time),
                        )
                        print(f"DEBUG Shift Confirmation SMS: mobile={mobile}")

                    elif new_status == 'rejected':
                        send_application_not_selected_sms(mobile, name, shift_name)
                        print(f"DEBUG App Rejected SMS: mobile={mobile}, name={name}")

            except Exception as e:
                print(f"SMS Error: {e}")

            status_msg = {
                'accepted': '✅ Application accepted successfully!',
                'reserved': '🔵 Application reserved.',
                'rejected': '❌ Application rejected.',
            }
            messages.success(request, status_msg[new_status])

    return redirect('shift_applicants', shift_id=application.shift.id)


@login_required
def update_onboard_status(request, app_id):
    application = get_object_or_404(
        ShiftApplication,
        id=app_id,
        shift__posted_by=request.user,
        status='accepted'
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        new_onboard = request.POST.get('onboard_status')

        # ── Mark Arrived (no OTP) ────────────────────────────
        if action == 'mark_arrived':
            application.onboard_status = 'arrived'
            application.save()
            messages.success(request, '✅ Marked as Arrived!')
            return redirect('shift_applicants', shift_id=application.shift.id)

       # ── OTP Generate & Send ──────────────────────────────
        elif action == 'send_otp':
            mobile = application.applicant.mobile
            print(f"DEBUG send_otp: mobile={repr(mobile)}")
            try:
                from users.models import OTP
                from users.sms_utils import send_shift_start_otp
                if mobile:
                    otp_code = OTP.generate(mobile, otp_type="shift_start")
                    print(f"DEBUG OTP generated: {otp_code}")
                    send_shift_start_otp(mobile, otp_code)
                    print(f"DEBUG OTP sent: mobile={mobile}, otp={otp_code}")
                    messages.success(request, f'✅ OTP sent to doctor!')
                else:
                    print("DEBUG: mobile is empty/None, skipping OTP send")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"SMS Error: {e}")
                messages.error(request, '❌ OTP send failed!')
            return redirect('shift_applicants', shift_id=application.shift.id)

        # ── OTP Verify & Status Update ────────────────────────
        elif action == 'verify_otp':
            shift_otp = request.POST.get('shift_otp', '').strip()
            try:
                from users.models import OTP
                otp_obj = OTP.objects.get(
                    mobile  = application.applicant.mobile,
                    otp     = shift_otp,
                    is_used = False
                )
                otp_obj.is_used = True
                otp_obj.save()
            except OTP.DoesNotExist:
                messages.error(request, '❌ Invalid OTP!')
                return redirect('shift_applicants', shift_id=application.shift.id)

            application.onboard_status = new_onboard
            application.save()
            messages.success(request, f'✅ Status updated: {new_onboard.title()}!')

            # Shift Completed SMS
            if new_onboard == 'completed':
                try:
                    from users.sms_utils import send_shift_completed_sms
                    mobile  = application.applicant.mobile
                    profile = None
                    try:
                        profile = application.applicant.doctor_profile
                    except:
                        try:
                            profile = application.applicant.nurse_profile
                        except:
                            pass
                    name     = getattr(profile, 'full_name', None) or application.applicant.username
                    hospital = application.shift.hospital_name
                    if mobile:
                        send_shift_completed_sms(mobile, name, hospital)
                        print(f"DEBUG Shift Completed SMS: mobile={mobile}")
                except Exception as e:
                    print(f"SMS Error: {e}")

    return redirect('shift_applicants', shift_id=application.shift.id)



# ─── Review (Doctor side) ─────────────────────────────────────
@login_required
def submit_review(request, app_id):
    application = get_object_or_404(
        ShiftApplication,
        id=app_id,
        applicant=request.user,
        status='accepted',
        onboard_status='completed'
    )

    existing = ShiftReview.objects.filter(
        application=application,
        reviewer_type='doctor'
    ).first()

    hospital_review = ShiftReview.objects.filter(
        application=application,
        reviewer_type='hospital'
    ).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            review               = form.save(commit=False)
            review.application   = application
            review.reviewer      = request.user
            review.reviewer_type = 'doctor'
            review.save()
            messages.success(request, '⭐ Review submitted successfully!')
            cfg = get_role_config(request.user)
            return redirect(cfg['applications_url'])
    else:
        form = ReviewForm(instance=existing)

    cfg = get_role_config(request.user)
    return render(request, 'doctors/submit_review.html', {
        'form':            form,
        'application':     application,
        'existing':        existing,
        'hospital_review': hospital_review,
        'base_template':   cfg['base'],
    })


# ─── Review (Hospital side) ───────────────────────────────────
@login_required
def submit_hospital_review(request, app_id):
    application = get_object_or_404(
        ShiftApplication,
        id=app_id,
        shift__posted_by=request.user,
        status='accepted',
        onboard_status='completed'
    )

    existing = ShiftReview.objects.filter(
        application=application,
        reviewer_type='hospital'
    ).first()

    doctor_review = ShiftReview.objects.filter(
        application=application,
        reviewer_type='doctor'
    ).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            review               = form.save(commit=False)
            review.application   = application
            review.reviewer      = request.user
            review.reviewer_type = 'hospital'
            review.save()
            messages.success(request, '⭐ Review submitted successfully!')
            return redirect('shift_applicants', shift_id=application.shift.id)
    else:
        form = ReviewForm(instance=existing)

    cfg = get_role_config(request.user)
    return render(request, 'doctors/submit_hospital_review.html', {
        'form':          form,
        'application':   application,
        'existing':      existing,
        'doctor_review': doctor_review,
        'base_template': cfg['base'],
    })


# ─── Profile Popup (AJAX) ─────────────────────────────────────
@login_required
def applicant_profile_ajax(request, app_id):
    application = get_object_or_404(
        ShiftApplication,
        id=app_id,
        shift__posted_by=request.user
    )

    profile = None
    try:
        profile = application.applicant.doctor_profile
    except Exception:
        try:
            profile = application.applicant.nurse_profile
        except Exception:
            pass

    return render(request, 'doctors/_profile_popup.html', {
        'profile':   profile,
        'applicant': application.applicant,
    })





import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

@login_required
@require_POST
def initiate_payment(request, app_id):
    """Payer (hospital/doctor/nurse) payment method choose karta hai"""
    app = get_object_or_404(
        ShiftApplication,
        id=app_id,
        shift__posted_by=request.user  # sirf shift poster hi pay karega
    )

    if app.onboard_status != 'completed':
        return JsonResponse({'error': 'Shift abhi complete nahi hui'}, status=400)

    if app.hospital_marked_paid:
        return JsonResponse({'error': 'Payment already initiated hai'}, status=400)

    data   = json.loads(request.body)
    method = data.get('method')

    if method not in ['upi', 'cash']:
        return JsonResponse({'error': 'Invalid method'}, status=400)

    app.payment_method = method
    app.save()

    if method == 'upi':
        locum = app.applicant
        try:
            if locum.role == 'doctor':
                upi_id    = locum.doctor_profile.upi_id
                full_name = locum.doctor_profile.full_name
            else:
                upi_id    = locum.nurse_profile.upi_id
                full_name = locum.nurse_profile.full_name
        except Exception:
            upi_id    = None
            full_name = locum.username

        if not upi_id:
            return JsonResponse({'error': 'Locum ne UPI ID profile mein set nahi ki hai'}, status=400)

        amount   = app.shift.pay
        upi_link = f"upi://pay?pa={upi_id}&pn={full_name}&am={amount}&cu=INR&tn=ProLocum+Shift+Payment"

        return JsonResponse({
            'success':  True,
            'method':   'upi',
            'upi_id':   upi_id,
            'upi_link': upi_link,
            'amount':   amount,
            'name':     full_name,
        })

    else:  # cash
        return JsonResponse({
            'success': True,
            'method':  'cash',
            'amount':  app.shift.pay,
        })


@login_required
@require_POST
def mark_paid(request, app_id):
    """Payer kehta hai maine pay kar diya"""
    app = get_object_or_404(
        ShiftApplication,
        id=app_id,
        shift__posted_by=request.user
    )

    if not app.payment_method:
        return JsonResponse({'error': 'Pehle payment method choose karo'}, status=400)

    app.hospital_marked_paid = True
    app.hospital_paid_at     = timezone.now()
    app.save()

    return JsonResponse({
        'success': True,
        'message': 'Payment marked! Locum confirmation pending hai.'
    })


@login_required
@require_POST
def locum_payment_response(request, app_id):
    """Locum (receiver) confirm ya reject karta hai"""
    app = get_object_or_404(
        ShiftApplication,
        id=app_id,
        applicant=request.user
    )

    if not app.hospital_marked_paid:
        return JsonResponse({'error': 'Payer ne abhi payment mark nahi ki'}, status=400)

    if app.payment_status == 'paid':
        return JsonResponse({'error': 'Payment already confirmed hai'}, status=400)

    data     = json.loads(request.body)
    received = data.get('received')  # True ya False

    if received:
        app.locum_confirmed_paid = True
        app.payment_status       = 'paid'
    else:
        app.locum_confirmed_paid = False
        app.payment_status       = 'disputed'

    app.save()

    return JsonResponse({
        'success':        True,
        'payment_status': app.payment_status
    })