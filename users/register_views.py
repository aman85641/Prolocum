from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from users.models import RegistrationDraft  # ← naya import

User = get_user_model()

DOCTOR_PROCEDURES = [
    'IM/SC/ID/IV Injection', 'IV Cannulation Peripheral', 'Dressing and Wound Care',
    'Suture', 'Urine Catheterization (Foleys)', 'Central Line IV', 'Intubation',
    'ABG Collection', 'Incision and Drainage', 'Pleural Tapping',
    'Ryles Tube Insertion', 'CPR', 'ECG Basic Interpretation',
    'ECG Recording', 'Vitals Monitoring (BP/Pulse/HGT)', 'Blood Collection',
]

NURSE_PROCEDURES = [
    'IM/SC/ID/IV Injection', 'IV Cannulation Peripheral', 'Dressing and Wound Care',
    'Urine Catheterization (Foleys)', 'Ryles Tube Insertion', 'CPR',
    'ECG Recording', 'Vitals Monitoring (BP/Pulse/HGT)', 'Blood Collection',
    'Oxygen Administration', 'Nebulization', 'Suctioning',
    'Tracheostomy Care', 'Colostomy Care', 'Bed Bath & Patient Hygiene',
]

HOSPITAL_SPECIALITIES = [
    'General Medicine', 'Emergency & Trauma', 'ICU / Critical Care',
    'Pediatrics', 'Gynecology & Obstetrics', 'Orthopedics', 'Cardiology',
    'Neurology', 'Oncology', 'Nephrology', 'Gastroenterology',
    'Pulmonology', 'ENT', 'Ophthalmology', 'Dermatology', 'Psychiatry',
]


def _is_admin(user):
    return user.role == 'admin' or user.is_staff or user.is_superuser


def _save_draft(user, role, step, step1_data=None, step2_data=None):
    """Helper — draft ek jagah se save hoga"""
    draft, _ = RegistrationDraft.objects.get_or_create(user=user)
    draft.role         = role
    draft.current_step = step
    if step1_data is not None:
        draft.step1_data = step1_data
    if step2_data is not None:
        draft.step2_data = step2_data
    draft.save()


def _delete_draft(user):
    """Registration complete — draft hatao"""
    RegistrationDraft.objects.filter(user=user).delete()


# ─────────────────────────────────────────
#  PROGRESS HELPERS — same rahenge
# ─────────────────────────────────────────

def get_doctor_progress(profile, current_step):
    step1_done = bool(profile and (profile.full_name or profile.registration_no))
    step2_done = bool(profile and profile.known_procedures)
    step3_done = bool(profile and (profile.profile_photo or profile.aadhar_photo))
    if current_step == 1: return 33 if step1_done else 0
    if current_step == 2: return 66 if step2_done else 33
    if current_step == 3: return 100 if step3_done else 66
    return 0

def get_nurse_progress(profile, current_step):
    step1_done = bool(profile and (profile.full_name or profile.registration_no))
    step2_done = bool(profile and profile.known_procedures)
    step3_done = bool(profile and (profile.profile_photo or profile.aadhar_photo))
    if current_step == 1: return 33 if step1_done else 0
    if current_step == 2: return 66 if step2_done else 33
    if current_step == 3: return 100 if step3_done else 66
    return 0

def get_hospital_progress(profile, current_step):
    step1_done = bool(profile and (profile.hospital_name or profile.registration_no))
    step2_done = bool(profile and (profile.logo or profile.registration_doc))
    if current_step == 1: return 50 if step1_done else 0
    if current_step == 2: return 100 if step2_done else 50
    return 0


# ═══════════════════════════════════════════════════════════
#  DOCTOR — STEP 1
# ═══════════════════════════════════════════════════════════

def doctor_register_step1(request):
    from doctors.models import DoctorProfile
 # ── DEBUG — hata dena baad mein ──
    print("=== STEP 1 DEBUG ===")
    print("Is authenticated:", request.user.is_authenticated)
    print("User:", request.user)
    print("Session key:", request.session.session_key)
    
    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.doctor_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except DoctorProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        profile, _ = DoctorProfile.objects.get_or_create(user=request.user)
        profile.full_name        = request.POST.get('full_name', '')
        profile.age              = request.POST.get('age') or None
        profile.sex              = request.POST.get('sex', '')
        profile.registration_no  = request.POST.get('registration_no', '')
        profile.qualification    = request.POST.get('qualification', '')
        profile.experience       = request.POST.get('experience', '')
        profile.address          = request.POST.get('address', '')
        profile.state            = request.POST.get('state', '')
        profile.city             = request.POST.get('city', '')
        profile.pincode          = request.POST.get('pincode', '')
        profile.ward_preferences = ','.join(request.POST.getlist('ward_preferences'))
        profile.save()

        if request.POST.get('action') == 'next':
            # ← Draft save karo
            _save_draft(
                user=request.user, role='doctor', step=2,
                step1_data={
                    'full_name':        profile.full_name,
                    'age':              str(profile.age or ''),
                    'sex':              profile.sex,
                    'registration_no':  profile.registration_no,
                    'qualification':    profile.qualification,
                    'experience':       profile.experience,
                    'address':          profile.address,
                    'state':            profile.state,
                    'city':             profile.city,
                    'pincode':          profile.pincode,
                    'ward_preferences': profile.get_ward_list(),
                }
            )
            return redirect('doctor_register_step2')

    profile_wards = profile.get_ward_list() if profile else []

    return render(request, 'doctors/register_step1.html', {
        'profile':       profile,
        'profile_wards': profile_wards,
        'role':          'doctor',
        'progress':      get_doctor_progress(profile, 1),
    })


# ═══════════════════════════════════════════════════════════
#  DOCTOR — STEP 2
# ═══════════════════════════════════════════════════════════

def doctor_register_step2(request):
    from doctors.models import DoctorProfile

    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.doctor_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except DoctorProfile.DoesNotExist:
        return redirect('doctor_register_step1')

    selected = profile.get_procedure_list() if profile.known_procedures else []

    if request.method == 'POST':
        if request.POST.get('action') == 'back':
            return redirect('doctor_register_step1')

        profile.known_procedures = ','.join(request.POST.getlist('procedures'))
        profile.save()

        if request.POST.get('action') == 'next':
            # ← Draft save karo
            _save_draft(
                user=request.user, role='doctor', step=3,
                step2_data={'procedures': request.POST.getlist('procedures')}
            )
            return redirect('doctor_register_step3')

    return render(request, 'doctors/register_step2.html', {
        'procedures': DOCTOR_PROCEDURES,
        'selected':   selected,
        'role':       'doctor',
        'step':       2,
        'progress':   get_doctor_progress(profile, 2),
    })


# ═══════════════════════════════════════════════════════════
#  DOCTOR — STEP 3
# ═══════════════════════════════════════════════════════════

from plans.utils import setup_free_credits

def doctor_register_step3(request):
    from doctors.models import DoctorProfile

    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.doctor_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except DoctorProfile.DoesNotExist:
        return redirect('doctor_register_step1')

    if request.method == 'POST':
        if request.POST.get('action') == 'back':
            return redirect('doctor_register_step2')

        if request.FILES.get('profile_photo'):
            profile.profile_photo = request.FILES['profile_photo']
        if request.FILES.get('aadhar_photo'):
            profile.aadhar_photo = request.FILES['aadhar_photo']
        if request.FILES.get('pan_card'):
            profile.pan_card = request.FILES['pan_card']
        if request.FILES.get('degree_photo'):
            profile.degree_photo = request.FILES['degree_photo']

        profile.registered_state         = request.POST.get('registered_state', '')
        profile.is_registration_complete = True
        profile.verification_status      = 'pending'
        profile.save()

        setup_free_credits(request.user)
        _delete_draft(request.user)  # ← Draft hatao

        return redirect('verification_pending')

    return render(request, 'doctors/register_step3.html', {
        'profile':  profile,
        'role':     'doctor',
        'step':     3,
        'progress': get_doctor_progress(profile, 3),
    })


# ═══════════════════════════════════════════════════════════
#  NURSE — STEP 1
# ═══════════════════════════════════════════════════════════

def nurse_register_step1(request):
    from nurses.models import NurseProfile

    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.nurse_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except NurseProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        profile, _ = NurseProfile.objects.get_or_create(user=request.user)
        profile.full_name        = request.POST.get('full_name', '')
        profile.age              = request.POST.get('age') or None
        profile.sex              = request.POST.get('sex', '')
        profile.registration_no  = request.POST.get('registration_no', '')
        profile.qualification    = request.POST.get('qualification', '')
        profile.experience       = request.POST.get('experience', '')
        profile.address          = request.POST.get('address', '')
        profile.state            = request.POST.get('state', '')
        profile.city             = request.POST.get('city', '')
        profile.pincode          = request.POST.get('pincode', '')
        profile.ward_preferences = ','.join(request.POST.getlist('ward_preferences'))
        profile.save()

        if request.POST.get('action') == 'next':
            _save_draft(
                user=request.user, role='nurse', step=2,
                step1_data={
                    'full_name':        profile.full_name,
                    'age':              str(profile.age or ''),
                    'sex':              profile.sex,
                    'registration_no':  profile.registration_no,
                    'qualification':    profile.qualification,
                    'experience':       profile.experience,
                    'address':          profile.address,
                    'state':            profile.state,
                    'city':             profile.city,
                    'pincode':          profile.pincode,
                    'ward_preferences': profile.get_ward_list(),
                }
            )
            return redirect('nurse_register_step2')

    profile_wards = profile.get_ward_list() if profile else []

    return render(request, 'nurses/register_step1.html', {
        'profile':       profile,
        'profile_wards': profile_wards,
        'role':          'nurse',
        'progress':      get_nurse_progress(profile, 1),
    })


# ═══════════════════════════════════════════════════════════
#  NURSE — STEP 2
# ═══════════════════════════════════════════════════════════

def nurse_register_step2(request):
    from nurses.models import NurseProfile

    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.nurse_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except NurseProfile.DoesNotExist:
        return redirect('nurse_register_step1')

    selected = profile.get_procedure_list() if profile.known_procedures else []

    if request.method == 'POST':
        if request.POST.get('action') == 'back':
            return redirect('nurse_register_step1')

        profile.known_procedures = ','.join(request.POST.getlist('procedures'))
        profile.save()

        if request.POST.get('action') == 'next':
            _save_draft(
                user=request.user, role='nurse', step=3,
                step2_data={'procedures': request.POST.getlist('procedures')}
            )
            return redirect('nurse_register_step3')

    return render(request, 'nurses/register_step2.html', {
        'procedures': NURSE_PROCEDURES,
        'selected':   selected,
        'role':       'nurse',
        'step':       2,
        'progress':   get_nurse_progress(profile, 2),
    })


# ═══════════════════════════════════════════════════════════
#  NURSE — STEP 3
# ═══════════════════════════════════════════════════════════

def nurse_register_step3(request):
    from nurses.models import NurseProfile

    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.nurse_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except NurseProfile.DoesNotExist:
        return redirect('nurse_register_step1')

    if request.method == 'POST':
        if request.POST.get('action') == 'back':
            return redirect('nurse_register_step2')

        if request.FILES.get('profile_photo'):
            profile.profile_photo = request.FILES['profile_photo']
        if request.FILES.get('aadhar_photo'):
            profile.aadhar_photo = request.FILES['aadhar_photo']
        if request.FILES.get('pan_card'):
            profile.pan_card = request.FILES['pan_card']
        if request.FILES.get('degree_photo'):
            profile.degree_photo = request.FILES['degree_photo']

        profile.registered_state         = request.POST.get('registered_state', '')
        profile.is_registration_complete = True
        profile.verification_status      = 'pending'
        profile.save()

        setup_free_credits(request.user)
        _delete_draft(request.user)  # ← Draft hatao

        return redirect('verification_pending')

    return render(request, 'nurses/register_step3.html', {
        'profile':  profile,
        'role':     'nurse',
        'step':     3,
        'progress': get_nurse_progress(profile, 3),
    })


# ═══════════════════════════════════════════════════════════
#  HOSPITAL — STEP 1
# ═══════════════════════════════════════════════════════════

def hospital_register_step1(request):
    from hospitals.models import HospitalProfile

    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.hospital_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except HospitalProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        profile, _ = HospitalProfile.objects.get_or_create(user=request.user)
        profile.hospital_name   = request.POST.get('hospital_name', '')
        profile.hospital_type   = request.POST.get('hospital_type', '')
        profile.registration_no = request.POST.get('registration_no', '')
        profile.contact_person  = request.POST.get('contact_person', '')
        profile.phone           = request.POST.get('phone', '')
        profile.email           = request.POST.get('email', '')
        profile.address         = request.POST.get('address', '')
        profile.state           = request.POST.get('state', '')
        profile.city            = request.POST.get('city', '')
        profile.pincode         = request.POST.get('pincode', '')
        profile.bed_count       = request.POST.get('bed_count') or None
        profile.specialities    = ','.join(request.POST.getlist('specialities'))
        profile.save()

        if request.POST.get('action') == 'next':
            _save_draft(
                user=request.user, role='hospital', step=2,
                step1_data={
                    'hospital_name':   profile.hospital_name,
                    'hospital_type':   profile.hospital_type,
                    'registration_no': profile.registration_no,
                    'contact_person':  profile.contact_person,
                    'phone':           profile.phone,
                    'email':           profile.email,
                    'address':         profile.address,
                    'state':           profile.state,
                    'city':            profile.city,
                    'pincode':         profile.pincode,
                    'bed_count':       str(profile.bed_count or ''),
                    'specialities':    profile.specialities.split(',') if profile.specialities else [],
                }
            )
            return redirect('hospital_register_step2')

    profile_specialities = profile.specialities.split(',') if profile and profile.specialities else []

    return render(request, 'hospitals/register_step1.html', {
        'profile':              profile,
        'profile_specialities': profile_specialities,
        'specialities_list':    HOSPITAL_SPECIALITIES,
        'role':                 'hospital',
        'progress':             get_hospital_progress(profile, 1),
    })


# ═══════════════════════════════════════════════════════════
#  HOSPITAL — STEP 2
# ═══════════════════════════════════════════════════════════
def hospital_register_step2(request):
    from hospitals.models import HospitalProfile

    if not request.user.is_authenticated:
        return redirect('home')
    if _is_admin(request.user):
        return redirect('admin:index')

    try:
        profile = request.user.hospital_profile
        if profile.is_registration_complete:
            return redirect('verification_pending')
    except HospitalProfile.DoesNotExist:
        return redirect('hospital_register_step1')

    if request.method == 'POST':
        if request.POST.get('action') == 'back':
            return redirect('hospital_register_step1')

        if request.FILES.get('logo'):
            profile.logo = request.FILES['logo']
        if request.FILES.get('registration_doc'):
            profile.registration_doc = request.FILES['registration_doc']
        # PURANA — hatao
        # if request.FILES.get('pan_card'):
        #     profile.pan_card = request.FILES['pan_card']

        # NAYA — aadhar_photo save karo
        if request.FILES.get('aadhar_photo'):
            profile.aadhar_photo = request.FILES['aadhar_photo']

        profile.registered_state         = request.POST.get('registered_state', '')
        profile.is_registration_complete = True
        profile.verification_status      = 'pending'
        profile.save()

        setup_free_credits(request.user)
        _delete_draft(request.user)

        return redirect('verification_pending')

    return render(request, 'hospitals/register_step2.html', {
        'profile':  profile,
        'role':     'hospital',
        'step':     2,
        'progress': get_hospital_progress(profile, 2),
    })
# ═══════════════════════════════════════════════════════════
#  VERIFICATION PENDING
# ═══════════════════════════════════════════════════════════

def verification_pending(request):
    user = request.user
    role = getattr(user, 'role', 'doctor')
    credentials = request.session.pop('new_credentials', None)

    profile = None
    try:
        if role == 'doctor':
            profile = user.doctor_profile
        elif role == 'nurse':
            profile = user.nurse_profile
        elif role == 'hospital':
            profile = user.hospital_profile
    except:
        pass

    rejected = getattr(profile, 'is_rejected', False) if profile else False

    return render(request, 'users/verification_pending.html', {
        'role':            role,
        'profile':         profile,
        'rejected':        rejected,
        'new_credentials': credentials,
    })