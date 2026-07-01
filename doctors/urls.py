# doctors/urls.py

from django.urls import path, include
from users import register_views
from . import views as doctor_views
from hospitals import views as hospital_views

urlpatterns = [
    # Registration steps
    path('register/step1/', register_views.doctor_register_step1, name='doctor_register_step1'),
    path('register/step2/', register_views.doctor_register_step2, name='doctor_register_step2'),
    path('register/step3/', register_views.doctor_register_step3, name='doctor_register_step3'),
    path('register/verification-pending/', register_views.verification_pending, name='verification_pending'),  # ✅ YEH ADD KARO

    # Dashboard
    path('dashboard/', doctor_views.dashboard, name='doctor_dashboard'),

    # Shifts
    path('shifts/', include('shifts.urls')),

    # Vacancies
    path('vacancies/', hospital_views.available_vacancies, name='available_vacancies'),
    path('vacancy/<int:vacancy_id>/', hospital_views.vacancy_detail, name='vacancy_detail'),
    path('vacancy/my-applications/', hospital_views.my_vacancy_applications, name='my_vacancy_applications'),
    path('vacancy/withdraw/<int:app_id>/', hospital_views.withdraw_vacancy_application, name='withdraw_vacancy_application'),

    path('profile/', doctor_views.my_profile, name='doctor_my_profile'),
    path('wallet/', doctor_views.my_wallet, name='doctor_wallet'),
]