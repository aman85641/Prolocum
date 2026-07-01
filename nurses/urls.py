from users import register_views

# nurses/urls.py

from django.urls import path
from . import views
from hospitals import views as hospital_views
from shifts import views as shift_views

urlpatterns = [
    path('register/step1/', register_views.nurse_register_step1, name='nurse_register_step1'),
    path('register/step2/', register_views.nurse_register_step2, name='nurse_register_step2'),
    path('register/step3/', register_views.nurse_register_step3, name='nurse_register_step3'),
    path('dashboard/',              views.dashboard,            name='nurse_dashboard'),
    path('shifts/available/',       views.available_shifts,     name='nurse_available_shifts'),
    path('shifts/detail/<int:shift_id>/', views.shift_detail,   name='nurse_shift_detail'),
    path('shifts/applied/<int:shift_id>/success/', views.shift_applied_success, name='nurse_shift_success'),
    path('shifts/post/',            views.post_new_shift,       name='nurse_post_shift'),
    path('shifts/posted/',          views.posted_shifts,        name='nurse_posted_shifts'),
    path('shifts/my-applications/', views.my_applications,      name='nurse_my_applications'),
    path('shifts/withdraw/<int:app_id>/', views.withdraw_application, name='nurse_withdraw_application'),
    path('shifts/deactivate/<int:shift_id>/', views.deactivate_shift, name='nurse_deactivate_shift'),
    path('shifts/applicants/<int:shift_id>/', shift_views.shift_applicants,       name='nurse_shift_applicants'),
    path('shifts/review/<int:app_id>/',       shift_views.submit_review,          name='nurse_submit_review'),        # ✅ Add
    path('shifts/hospital-review/<int:app_id>/', shift_views.submit_hospital_review, name='nurse_hospital_review'),  # ✅ Add
    path('shifts/application/update/<int:app_id>/',  shift_views.update_application_status, name='nurse_update_application_status'),  # ✅ Add
    path('shifts/application/onboard/<int:app_id>/', shift_views.update_onboard_status,     name='nurse_update_onboard_status'),      # ✅ Add

    path('vacancies/', hospital_views.available_vacancies, name='available_vacancies'),
    path('vacancy/<int:vacancy_id>/', hospital_views.vacancy_detail, name='vacancy_detail'),
    path('vacancy/my-applications/', hospital_views.my_vacancy_applications, name='my_vacancy_applications'),
    path('vacancy/withdraw/<int:app_id>/', hospital_views.withdraw_vacancy_application, name='withdraw_vacancy_application'),
    path('profile/', views.my_profile, name='nurse_my_profile'),
    path('shifts/edit/<int:shift_id>/',   views.edit_shift,   name='nurse_edit_shift'),
path('shifts/delete/<int:shift_id>/', views.delete_shift, name='nurse_delete_shift'),

path('wallet/', views.my_wallet, name='nurse_wallet'),

]