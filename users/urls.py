from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/<str:role>/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('doctor-type/', views.doctor_type_view, name='doctor_type'),
    path('otp/verify/', views.verify_otp, name='verify_otp'),        # ✅ Pehle
    path('otp/<str:role>/', views.send_otp, name='send_otp'),        # ✅ Baad mein
    path('forgot-password/', views.forgot_password, name='forgot_password'),

     path('send-mobile-otp/', views.send_mobile_otp, name='send_mobile_otp'),
    path('verify-mobile-otp/', views.verify_mobile_otp, name='verify_mobile_otp'),
]