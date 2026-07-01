# shifts/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ── Applicant (doctor/nurse) side ──────────────────────────
    path('available/',                          views.available_shifts,         name='available_shifts'),
    path('detail/<int:shift_id>/',              views.shift_detail,             name='shift_detail'),
    path('applied/<int:shift_id>/success/',     views.shift_applied_success,    name='shift_applied_success'),
    path('my-applications/',                    views.my_applications,          name='my_applications'),
    path('withdraw/<int:app_id>/',              views.withdraw_application,     name='withdraw_application'),
    path('review/<int:app_id>/',                views.submit_review,            name='submit_review'),

    # ── Poster (hospital) side ──────────────────────────────────
    path('post/',                               views.post_new_shift,           name='post_new_shift'),
    path('posted/',                             views.posted_shifts,            name='posted_shifts'),
    path('deactivate/<int:shift_id>/',          views.deactivate_shift,         name='deactivate_shift'),
    path('applicants/<int:shift_id>/',          views.shift_applicants,         name='shift_applicants'),
    path('application/update/<int:app_id>/',    views.update_application_status, name='update_application_status'),
    path('application/onboard/<int:app_id>/',   views.update_onboard_status,    name='update_onboard_status'),
    path('application/hospital-review/<int:app_id>/', views.submit_hospital_review, name='submit_hospital_review'),

    # ── AJAX ───────────────────────────────────────────────────
    path('profile-popup/<int:app_id>/',         views.applicant_profile_ajax,   name='applicant_profile_ajax'),

    path('edit/<int:shift_id>/',   views.edit_shift,   name='edit_shift'),
path('delete/<int:shift_id>/', views.delete_shift, name='delete_shift'),

path('payment/initiate/<int:app_id>/',       views.initiate_payment,       name='initiate_payment'),
path('payment/mark-paid/<int:app_id>/',      views.mark_paid,              name='mark_paid'),
path('payment/locum-response/<int:app_id>/', views.locum_payment_response, name='locum_payment_response'),
]