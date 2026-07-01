from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from doctors.models import DoctorProfile
from nurses.models import NurseProfile
from hospitals.models import HospitalProfile

User = get_user_model()

def is_admin(user):
    return user.is_authenticated and user.is_staff


def _common(request):
    return {
        'pending_doctors':   DoctorProfile.objects.filter(verification_status='pending').count(),
        'pending_nurses':    NurseProfile.objects.filter(verification_status='pending').count(),
        'pending_hospitals': HospitalProfile.objects.filter(verification_status='pending').count(),
    }


# ─── Dashboard ───────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def dashboard(request):
    try:
        from shifts.models import Shift, ShiftApplication
        total_shifts      = Shift.objects.count()
        active_shifts     = Shift.objects.filter(is_active=True).count()
        total_applications = ShiftApplication.objects.count()
        completed_shifts  = ShiftApplication.objects.filter(onboard_status='completed').count()
    except:
        total_shifts = active_shifts = total_applications = completed_shifts = 0

    try:
        from hospitals.models import Vacancy, VacancyApplication
        total_vacancies   = Vacancy.objects.count()
        total_vac_apps    = VacancyApplication.objects.count()
    except:
        total_vacancies = total_vac_apps = 0

    recent = []
    for p in DoctorProfile.objects.order_by('-created_at')[:5]:
        recent.append({'name': p.full_name, 'role': 'doctor', 'id': p.id, 'status': p.verification_status, 'created_at': p.created_at})
    for p in NurseProfile.objects.order_by('-created_at')[:5]:
        recent.append({'name': p.full_name, 'role': 'nurse', 'id': p.id, 'status': p.verification_status, 'created_at': p.created_at})
    for p in HospitalProfile.objects.order_by('-created_at')[:5]:
        recent.append({'name': p.hospital_name, 'role': 'hospital', 'id': p.id, 'status': p.verification_status, 'created_at': p.created_at})
    recent.sort(key=lambda x: x['created_at'], reverse=True)

    ctx = _common(request)
    ctx.update({
        'total_doctors':      DoctorProfile.objects.count(),
        'total_nurses':       NurseProfile.objects.count(),
        'total_hospitals':    HospitalProfile.objects.count(),
        'total_approved':     (
            DoctorProfile.objects.filter(verification_status='approved').count() +
            NurseProfile.objects.filter(verification_status='approved').count() +
            HospitalProfile.objects.filter(verification_status='approved').count()
        ),
        'total_users':        User.objects.count(),
        'total_shifts':       total_shifts,
        'active_shifts':      active_shifts,
        'total_applications': total_applications,
        'completed_shifts':   completed_shifts,
        'total_vacancies':    total_vacancies,
        'total_vac_apps':     total_vac_apps,
        'recent_applications': recent[:10],
    })
    return render(request, 'admin_panel/dashboard.html', ctx)


# ─── Applications ─────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def applications(request):
    role   = request.GET.get('role', 'doctor')
    status = request.GET.get('status', 'all')
    MODEL_MAP = {'doctor': DoctorProfile, 'nurse': NurseProfile, 'hospital': HospitalProfile}
    Model = MODEL_MAP.get(role, DoctorProfile)
    qs = Model.objects.all().order_by('-created_at')
    if status != 'all':
        qs = qs.filter(verification_status=status)
    ctx = _common(request)
    ctx.update({'profiles': qs, 'role': role, 'status': status})
    return render(request, 'admin_panel/applications.html', ctx)


# ─── Application Detail ───────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def application_detail(request, role, pk):
    MODEL_MAP = {'doctor': DoctorProfile, 'nurse': NurseProfile, 'hospital': HospitalProfile}
    profile = get_object_or_404(MODEL_MAP.get(role, DoctorProfile), pk=pk)
    
    # views.py mein application_detail function mein
    specialities_list = []
    if hasattr(profile, 'specialities') and profile.specialities:
        specialities_list = [s.strip() for s in profile.specialities.split(',') if s.strip()]
    
    procedures_list = []
    if hasattr(profile, 'known_procedures') and profile.known_procedures:
        procedures_list = [s.strip() for s in profile.known_procedures.split(',') if s.strip()]
    
    wards_list = []
    if hasattr(profile, 'ward_preferences') and profile.ward_preferences:
        wards_list = [s.strip() for s in profile.ward_preferences.split(',') if s.strip()]
    
    ctx = _common(request)
    ctx.update({
        'profile': profile,
        'role': role,
        'specialities_list': specialities_list,
        'procedures_list': procedures_list,
        'wards_list': wards_list,
    })
    return render(request, 'admin_panel/application_detail.html', ctx)

# ─── Verify Application ───────────────────────────────────────
# ─── Verify Application ───────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def verify_application(request, role, pk):
    MODEL_MAP = {'doctor': DoctorProfile, 'nurse': NurseProfile, 'hospital': HospitalProfile}
    profile = get_object_or_404(MODEL_MAP.get(role, DoctorProfile), pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            profile.verification_status = 'approved'
            profile.is_verified = True
            try:
                from users.sms_utils import send_account_verified_sms
                mobile = profile.user.mobile
                name = getattr(profile, 'full_name', None) or getattr(profile, 'hospital_name', None) or mobile
                if mobile:
                    send_account_verified_sms(mobile, name)
            except Exception as e:
                print(f"SMS Error: {e}")
            profile.save()

        elif action == 'reject':
            profile.verification_status = 'rejected'
            profile.is_verified = False
            profile.save()

        elif action == 'delete':
            user = profile.user
            profile.delete()
            user.delete()
            return redirect('admin_applications')  # profile delete ho gaya, detail pe mat jao

    return redirect('admin_application_detail', role=role, pk=pk)


@login_required
@user_passes_test(is_admin)
def user_list(request):
    role   = request.GET.get('role', 'all')
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')

    users = User.objects.all().order_by('-date_joined')

    if role != 'all':
        users = users.filter(role=role)

    if search:
        users = users.filter(username__icontains=search)

    if status == 'banned':
        users = users.filter(is_active=False)

    ctx = _common(request)
    ctx.update({'users': users, 'role': role, 'search': search, 'status': status})
    return render(request, 'admin_panel/user_list.html', ctx)


@login_required
@user_passes_test(is_admin)
def user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
    return redirect('admin_user_list')

@login_required
@user_passes_test(is_admin)
def shift_list(request):
    from shifts.models import Shift, ShiftApplication
    
    status = request.GET.get('status', 'all')
    shifts = Shift.objects.select_related('posted_by').prefetch_related(
        'applications',
        'applications__applicant',
        'applications__applicant__doctor_profile',
        'applications__applicant__nurse_profile',
    ).order_by('-created_at')
    
    if status == 'active':
        shifts = shifts.filter(is_active=True)
    elif status == 'inactive':
        shifts = shifts.filter(is_active=False)
    elif status == 'urgent':
        shifts = shifts.filter(is_urgent=True, is_active=True)
    elif status == 'disputed':
        shifts = shifts.filter(applications__payment_status='disputed').distinct()

    ctx = _common(request)
    ctx.update({'shifts': shifts, 'status': status})
    return render(request, 'admin_panel/shift_list.html', ctx)


@login_required
@user_passes_test(is_admin)
def shift_deactivate(request, pk):
    from shifts.models import Shift
    shift = get_object_or_404(Shift, pk=pk)
    if request.method == 'POST':
        shift.is_active = False
        shift.save()
    return redirect('admin_shift_list')


# ─── Vacancy Management ───────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def vacancy_list(request):
    from hospitals.models import Vacancy
    status = request.GET.get('status', 'all')
    vacancies = Vacancy.objects.select_related('posted_by').order_by('-created_at')
    if status == 'active':
        vacancies = vacancies.filter(is_active=True)
    elif status == 'inactive':
        vacancies = vacancies.filter(is_active=False)
    elif status == 'urgent':
        vacancies = vacancies.filter(is_urgent=True, is_active=True)
    ctx = _common(request)
    ctx.update({'vacancies': vacancies, 'status': status})
    return render(request, 'admin_panel/vacancy_list.html', ctx)


@login_required
@user_passes_test(is_admin)
def vacancy_deactivate(request, pk):
    from hospitals.models import Vacancy
    vacancy = get_object_or_404(Vacancy, pk=pk)
    if request.method == 'POST':
        vacancy.is_active = False
        vacancy.save()
    return redirect('admin_vacancy_list')


# ─── Reports ─────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def reports(request):
    from shifts.models import Shift, ShiftApplication
    from hospitals.models import Vacancy, VacancyApplication

    # Shift stats
    shift_stats = {
        'total':     Shift.objects.count(),
        'active':    Shift.objects.filter(is_active=True).count(),
        'urgent':    Shift.objects.filter(is_urgent=True).count(),
        'completed': ShiftApplication.objects.filter(onboard_status='completed').count(),
    }

    # Application stats
    app_stats = {
        'total':    ShiftApplication.objects.count(),
        'accepted': ShiftApplication.objects.filter(status='accepted').count(),
        'rejected': ShiftApplication.objects.filter(status='rejected').count(),
        'withdrawn':ShiftApplication.objects.filter(status='withdrawn').count(),
    }

    # Vacancy stats
    vac_stats = {
        'total':    Vacancy.objects.count(),
        'active':   Vacancy.objects.filter(is_active=True).count(),
        'urgent':   Vacancy.objects.filter(is_urgent=True).count(),
    }

    vac_app_stats = {
        'total':    VacancyApplication.objects.count(),
        'accepted': VacancyApplication.objects.filter(status='accepted').count(),
        'rejected': VacancyApplication.objects.filter(status='rejected').count(),
    }

    # User stats
    user_stats = {
        'total':     User.objects.count(),
        'doctors':   User.objects.filter(role='doctor').count(),
        'nurses':    User.objects.filter(role='nurse').count(),
        'hospitals': User.objects.filter(role='hospital').count(),
        'active':    User.objects.filter(is_active=True).count(),
        'inactive':  User.objects.filter(is_active=False).count(),
    }

    ctx = _common(request)
    ctx.update({
        'shift_stats':    shift_stats,
        'app_stats':      app_stats,
        'vac_stats':      vac_stats,
        'vac_app_stats':  vac_app_stats,
        'user_stats':     user_stats,
    })
    return render(request, 'admin_panel/reports.html', ctx)



# admin/views.py mein add karo

from django.http import JsonResponse
from .models import City

def get_cities(request):
    state = request.GET.get('state', '').strip()
    q     = request.GET.get('q', '').strip()
    
    cities = City.objects.all()
    if state:
        cities = cities.filter(state__iexact=state)
    if q:
        cities = cities.filter(name__icontains=q)
    
    data = list(cities.values('id', 'name', 'state'))
    return JsonResponse({'cities': data})


from .models import City

def admin_city_list(request):
    query  = request.GET.get('q', '').strip()
    state  = request.GET.get('state', '').strip()
    cities = City.objects.all()
    if query:
        cities = cities.filter(name__icontains=query)
    if state:
        cities = cities.filter(state__iexact=state)
    states = City.objects.values_list('state', flat=True).distinct().order_by('state')
    return render(request, 'admin_panel/cities.html', {
        'cities': cities,
        'states': states,
        'query':  query,
        'selected_state': state,
    })

def admin_city_add(request):
    if request.method == 'POST':
        name  = request.POST.get('name', '').strip()
        state = request.POST.get('state', '').strip()
        if name and state:
            City.objects.get_or_create(name=name, state=state)
        return redirect('admin_city_list')
    return redirect('admin_city_list')

def admin_city_delete(request, pk):
    City.objects.filter(pk=pk).delete()
    return redirect('admin_city_list')