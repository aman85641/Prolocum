from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from hospitals.models import HospitalProfile
from plans.utils import can_post_shift, use_shift_post_limit, can_post_vacancy, use_vacancy_post_limit, can_apply_vacancy, use_vacancy_limit

try:
    from shifts.models import Shift, ShiftApplication
    SHIFTS_ENABLED = True
except ImportError:
    SHIFTS_ENABLED = False


from plans.utils import can_post_shift, use_shift_post_limit, can_post_vacancy, use_vacancy_post_limit, can_apply_vacancy, use_vacancy_limit, get_active_plan

@login_required
def dashboard(request):
    try:
        profile = request.user.hospital_profile
    except HospitalProfile.DoesNotExist:
        return redirect('hospital_register_step1')

    credentials = request.session.pop('new_credentials', None)

    # ── Plan check ──────────────────────────────────────────────
    active_plan        = get_active_plan(request.user)
    can_post_shift_ok  = False
    can_post_vacancy_ok = False

    if active_plan and active_plan.plan:
        p = active_plan.plan
        can_post_shift_ok   = p.shift_post_enabled
        can_post_vacancy_ok = p.vacancy_post_enabled

    context = {
        'profile':           profile,
        'credentials':       credentials,
        'posted_count':      0,
        'active_count':      0,
        'total_applicants':  0,
        'accepted_count':    0,
        'recent_shifts':     [],
        'urgent_count':      0,
        'can_post_shift':    can_post_shift_ok,
        'can_post_vacancy':  can_post_vacancy_ok,
        'active_plan':       active_plan,
    }

    if SHIFTS_ENABLED:
        posted_shifts = Shift.objects.filter(posted_by=request.user)
        recent_shifts = posted_shifts.order_by('-created_at')[:3]

        context['posted_count']     = posted_shifts.count()
        context['active_count']     = posted_shifts.filter(is_active=True).count()
        context['total_applicants'] = ShiftApplication.objects.filter(
            shift__posted_by=request.user
        ).exclude(status='withdrawn').count()
        context['accepted_count']   = ShiftApplication.objects.filter(
            shift__posted_by=request.user, status='accepted'
        ).count()
        context['recent_shifts']    = recent_shifts
        context['urgent_count']     = posted_shifts.filter(is_urgent=True, is_active=True).count()

    return render(request, 'hospitals/dashboard.html', context)

# ─── Available Shifts ─────────────────────────────────────────
@login_required
def available_shifts(request):
    shifts = Shift.objects.filter(
        is_active=True
    ).exclude(posted_by=request.user).order_by('-is_urgent', '-created_at')

    applied_ids = ShiftApplication.objects.filter(
        applicant=request.user,
        status__in=['applied', 'accepted', 'reserved']
    ).values_list('shift_id', flat=True)

    return render(request, 'doctors/available_shifts.html', {
        'shifts': shifts,
        'applied_ids': list(applied_ids),
        'base_template': 'hospitals/base.html',
        'detail_url_name': 'shift_detail',
    })


# ─── Post New Shift ───────────────────────────────────────────
@login_required
def post_new_shift(request):
    from shifts.forms import ShiftForm
    from plans.utils import can_post_shift, use_shift_post_limit, get_active_plan

    # ✅ Pehle hi calculate karo — GET aur POST dono ke liye
    user_plan = get_active_plan(request.user)
    can_post_urgent = bool(user_plan and user_plan.plan.urgent_shift_post_enabled)

    if request.method == 'POST':
        can_post, msg = can_post_shift(request.user)
        if not can_post:
            messages.error(request, f'❌ {msg}')
            return redirect('hospital_posted_shifts')

        form = ShiftForm(request.POST)
        if form.is_valid():
            shift = form.save(commit=False)
            shift.posted_by = request.user

            # ✅ Urgent permission check
            if shift.is_urgent and not can_post_urgent:
                shift.is_urgent = False

            shift.save()
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
            return redirect('hospital_posted_shifts')
    else:
        form = ShiftForm()

    return render(request, 'doctors/post_new_shift.html', {
        'form':            form,
        'base_template':   'hospitals/base.html',
        'cancel_url':      'hospital_posted_shifts',
        'default_role':    'both',
        'role_locked':     False,
        'can_post_urgent': can_post_urgent,
    })

# ─── Posted Shifts ────────────────────────────────────────────
@login_required
def posted_shifts(request):
    shifts = Shift.objects.filter(
        posted_by=request.user
    ).order_by('-created_at')
    return render(request, 'doctors/posted_shifts.html', {
        'shifts': shifts,
        'base_template': 'hospitals/base.html',
        'post_url': 'hospital_post_shift',
        'deactivate_url': 'hospital_deactivate_shift',
    })


# ─── Deactivate Shift ─────────────────────────────────────────
@login_required
def deactivate_shift(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id, posted_by=request.user)
    shift.is_active = False
    shift.save()
    messages.success(request, 'Shift deactivated successfully.')
    return redirect('hospital_posted_shifts')


# ─────────────────────────────────────────────────────────────
# VACANCY VIEWS
# ─────────────────────────────────────────────────────────────

from .models import Vacancy, VacancyApplication
from .forms import VacancyForm


@login_required
def post_vacancy(request):
    if request.method == 'POST':

        can_post, msg = can_post_vacancy(request.user)
        if not can_post:
            messages.error(request, f' {msg}')
            return redirect('hospital_posted_vacancies')

        form = VacancyForm(request.POST)
        if form.is_valid():
            vacancy = form.save(commit=False)
            vacancy.posted_by = request.user
            vacancy.save()
            use_vacancy_post_limit(request.user)
            messages.success(request, 'Vacancy posted successfully!')
            return redirect('hospital_posted_vacancies')

        return render(request, 'hospitals/post_vacancy_form.html', {
            'form': form,
            'shift_type': request.POST.get('shift_type', 'single'),
        })

    else:
        shift_type = 'single'
        form = VacancyForm()
        try:
            profile = request.user.hospital_profile
            form.initial['hospital_name'] = profile.hospital_name
            form.initial['location']      = profile.address
            form.initial['city']          = profile.city
            form.initial['state']         = profile.state
            form.initial['contact_email'] = profile.email if hasattr(profile, 'email') else ''
            form.initial['contact_phone'] = profile.phone if hasattr(profile, 'phone') else ''
        except Exception:
            pass
        return render(request, 'hospitals/post_vacancy_form.html', {
            'form': form,
            'shift_type': shift_type,
        })

@login_required
def available_vacancies(request):
    role = getattr(request.user, 'role', 'doctor')
    now = timezone.now().date()

    vacancies = Vacancy.objects.filter(is_active=True).exclude(posted_by=request.user).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__gte=now)
    )

    if role == 'doctor':
        try:
            user_qual = request.user.doctor_profile.qualification
        except:
            user_qual = None

        vacancies = vacancies.filter(staff_type='doctor')
        if user_qual:
            if user_qual in ('bams', 'bhms'):
                # ✅ bams/bhms user ko exact match + bams_bhms vacancies bhi dikhao
                vacancies = vacancies.filter(
                    Q(doctor_qualification=user_qual) | Q(doctor_qualification='bams_bhms')
                )
            else:
                vacancies = vacancies.filter(doctor_qualification=user_qual)

    elif role == 'nurse':
        vacancies = vacancies.filter(staff_type='nurse')

    vacancies = vacancies.order_by('-is_urgent', '-created_at')

    applied_ids = VacancyApplication.objects.filter(
        applicant=request.user,
        status__in=['applied', 'accepted']
    ).values_list('vacancy_id', flat=True)

    return render(request, 'hospitals/available_vacancies.html', {
        'vacancies':     vacancies,
        'applied_ids':   list(applied_ids),
        'base_template': _get_base(request.user),
    })

# ─── Posted Vacancies (Hospital) ─────────────────────────────
@login_required
def posted_vacancies(request):
    vacancies = Vacancy.objects.filter(
        posted_by=request.user
    ).order_by('-created_at')
    return render(request, 'hospitals/posted_vacancies.html', {
        'vacancies': vacancies,
    })


# ─── Vacancy Applicants ───────────────────────────────────────
@login_required
def vacancy_applicants(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id, posted_by=request.user)
    applications = vacancy.applications.select_related('applicant').exclude(
        status='withdrawn'
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
        applicants_data.append({
            'application': app,
            'profile': profile,
        })

    return render(request, 'hospitals/vacancy_applicants.html', {
        'vacancy': vacancy,
        'applicants_data': applicants_data,
    })


# ─── Accept / Reject Vacancy Application ─────────────────────
@login_required
def update_vacancy_application(request, app_id):
    application = get_object_or_404(
        VacancyApplication,
        id=app_id,
        vacancy__posted_by=request.user
    )
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['accepted', 'rejected']:
            application.status = new_status
            application.save()
            msg = {'accepted': ' Application accepted!', 'rejected': ' Application rejected.'}
            messages.success(request, msg[new_status])
    return redirect('vacancy_applicants', vacancy_id=application.vacancy.id)


# ─── Deactivate Vacancy ───────────────────────────────────────
@login_required
def deactivate_vacancy(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id, posted_by=request.user)
    vacancy.is_active = False
    vacancy.save()
    messages.success(request, 'Vacancy deactivated successfully.')
    return redirect('hospital_posted_vacancies')


# ─────────────────────────────────────────────────────────────
# DOCTOR / NURSE SIDE
# ─────────────────────────────────────────────────────────────

def _get_base(user):
    role = getattr(user, 'role', 'doctor')
    return {
        'doctor':   'doctors/base.html',
        'nurse':    'nurses/base.html',
        'hospital': 'hospitals/base.html',
    }.get(role, 'doctors/base.html')


from django.db.models import Q
from django.utils import timezone



# ─── Vacancy Detail + Apply (Doctor/Nurse) ───────────────────
@login_required
def vacancy_detail(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id, is_active=True)
    already_applied = VacancyApplication.objects.filter(
        vacancy=vacancy, applicant=request.user
    ).first()

    if request.method == 'POST':
        if already_applied:
            messages.warning(request, 'You have already applied for this vacancy.')
        else:
            can_apply, msg = can_apply_vacancy(request.user)
            if not can_apply:
                messages.error(request, f'❌ {msg}')
                return redirect('vacancy_detail', vacancy_id=vacancy_id)

            from plans.utils import get_active_plan
            active_plan = get_active_plan(request.user)
            plan = active_plan.plan if active_plan else None

            if plan and plan.vacancy_apply_enabled:

                if plan.unlimited_vacancy_apply:
                    # Unlimited — seedha apply
                    pass

                elif plan.vacancy_limit > 0:
                    # Limit-based — limit use karo
                    use_vacancy_limit(request.user)

                else:
                    # Limit 0 + unlimited nahi → tokens katao
                    from plans.utils import deduct_shift_token
                    success, token_msg = deduct_shift_token(
                        request.user,
                        shift=vacancy,  # vacancy object pass karo
                        token_cost=1
                    )
                    if not success:
                        messages.error(request, f'❌ {token_msg}')
                        return redirect('vacancy_detail', vacancy_id=vacancy_id)

            VacancyApplication.objects.create(vacancy=vacancy, applicant=request.user)
            messages.success(request, '✅ Application submitted successfully!')
            return redirect('my_vacancy_applications')

    return render(request, 'hospitals/vacancy_detail.html', {
        'vacancy': vacancy,
        'already_applied': already_applied,
        'base_template': _get_base(request.user),
    })
# ─── My Vacancy Applications (Doctor/Nurse) ──────────────────
@login_required
def my_vacancy_applications(request):
    applications = VacancyApplication.objects.filter(
        applicant=request.user
    ).select_related('vacancy').order_by('-applied_at')

    return render(request, 'hospitals/my_vacancy_applications.html', {
        'applications': applications,
        'base_template': _get_base(request.user),
    })


# ─── Withdraw Vacancy Application ────────────────────────────
@login_required
def withdraw_vacancy_application(request, app_id):
    application = get_object_or_404(VacancyApplication, id=app_id, applicant=request.user)
    if application.status == 'applied':
        application.status = 'withdrawn'
        application.save()
        messages.success(request, 'Application withdrawn successfully.')
    else:
        messages.warning(request, 'This application cannot be withdrawn.')
    return redirect('my_vacancy_applications')


# ─── Profile Popup AJAX ───────────────────────────────────────
@login_required
def vacancy_applicant_profile_ajax(request, app_id):
    from .models import VacancyApplication
    application = get_object_or_404(VacancyApplication, id=app_id)
    profile = None
    try:
        profile = application.applicant.doctor_profile
    except Exception:
        try:
            profile = application.applicant.nurse_profile
        except Exception:
            pass

    return render(request, 'doctors/_profile_popup.html', {
        'profile': profile,
        'applicant': application.applicant,
    })


# ─── My Profile ───────────────────────────────────────────────
HOSPITAL_SPECIALITIES = [
    'General Medicine', 'Emergency & Trauma', 'ICU / Critical Care',
    'Pediatrics', 'Gynecology & Obstetrics', 'Orthopedics', 'Cardiology',
    'Neurology', 'Oncology', 'Nephrology', 'Gastroenterology',
    'Pulmonology', 'ENT', 'Ophthalmology', 'Dermatology', 'Psychiatry',
]

@login_required
def my_profile(request):
    profile = request.user.hospital_profile
    user    = request.user
    success = None
    error   = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile.hospital_name  = request.POST.get('hospital_name', profile.hospital_name)
            profile.hospital_type  = request.POST.get('hospital_type', profile.hospital_type)
            profile.contact_person = request.POST.get('contact_person', profile.contact_person)
            profile.phone          = request.POST.get('phone', profile.phone)
            profile.email          = request.POST.get('email', profile.email)
            profile.address        = request.POST.get('address', profile.address)
            profile.city           = request.POST.get('city', profile.city)
            profile.state          = request.POST.get('state', profile.state)
            profile.pincode        = request.POST.get('pincode', profile.pincode)
            profile.specialities   = request.POST.get('specialities', profile.specialities)
            profile.bed_count      = request.POST.get('bed_count') or profile.bed_count
            if 'logo' in request.FILES:
                profile.logo = request.FILES['logo']
            if 'registration_doc' in request.FILES:
                profile.registration_doc = request.FILES['registration_doc']
            if 'pan_card' in request.FILES:
                profile.pan_card = request.FILES['pan_card']
            profile.save()
            success = 'Profile updated successfully!'

        elif action == 'update_photo':
            if 'logo' in request.FILES:
                profile.logo = request.FILES['logo']
                profile.save()
                success = 'Hospital logo updated successfully!'

        elif action == 'update_specialities':
            profile.specialities = ','.join(request.POST.getlist('specialities'))
            profile.save()
            success = 'Specialities updated successfully!'

        elif action == 'change_password':
            old_pass = request.POST.get('old_password')
            new_pass = request.POST.get('new_password')
            confirm  = request.POST.get('confirm_password')
            if not user.check_password(old_pass):
                error = 'Old password is incorrect'
            elif new_pass != confirm:
                error = 'Passwords do not match'
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
            U = get_user_model()
            if U.objects.filter(username=new_username).exclude(id=user.id).exists():
                error = 'This username is already taken'
            else:
                user.username = new_username
                user.save()
                success = 'Username changed successfully!'

    selected_specialities = profile.specialities.split(',') if profile.specialities else []

    return render(request, 'hospitals/my_profile.html', {
        'profile':               profile,
        'user':                  user,
        'success':               success,
        'error':                 error,
        'specialities_list':     HOSPITAL_SPECIALITIES,
        'selected_specialities': selected_specialities,
    })

@login_required
def my_wallet(request):
    from plans.models import UserPlan
    try:
        current_plan = UserPlan.objects.filter(user=request.user, is_active=True).first()
        plan_history = UserPlan.objects.filter(user=request.user).select_related('plan').order_by('-bought_at')
    except:
        current_plan = None
        plan_history = []

    return render(request, 'hospitals/wallet.html', {
        'current_plan': current_plan,
        'plan_history': plan_history,
        'user':         request.user,
    })