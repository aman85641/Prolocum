from django.urls import path, include
from users import register_views
from . import views as hospital_views

urlpatterns = [
    # Registration
    path('register/step1/', register_views.hospital_register_step1, name='hospital_register_step1'),
    path('register/step2/', register_views.hospital_register_step2, name='hospital_register_step2'),

    # Dashboard
    path('dashboard/', hospital_views.dashboard, name='hospital_dashboard'),

    # Shifts - hospitals/shifts/ prefix ke saath
    path('shifts/', include('shifts.urls')),

     # ── Vacancy (Hospital side) ──────────────────────────────
    path('vacancy/post/',                           hospital_views.post_vacancy,                name='hospital_post_vacancy'),
    path('vacancy/posted/',                         hospital_views.posted_vacancies,            name='hospital_posted_vacancies'),
    path('vacancy/<int:vacancy_id>/applicants/',    hospital_views.vacancy_applicants,          name='vacancy_applicants'),
    path('vacancy/application/<int:app_id>/update/', hospital_views.update_vacancy_application, name='update_vacancy_application'),
    path('vacancy/<int:vacancy_id>/deactivate/',    hospital_views.deactivate_vacancy,          name='deactivate_vacancy'),
    path('vacancy/application/profile-popup/<int:app_id>/', 
     hospital_views.vacancy_applicant_profile_ajax, 
     name='vacancy_applicant_profile_ajax'),
path('wallet/', hospital_views.my_wallet, name='hospital_wallet'),
     path('profile/', hospital_views.my_profile, name='hospital_my_profile'),
]