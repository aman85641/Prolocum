from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                          views.dashboard,            name='admin_dashboard'),
    path('applications/',                       views.applications,         name='admin_applications'),
    path('application/<str:role>/<int:pk>/',    views.application_detail,   name='admin_application_detail'),
    path('verify/<str:role>/<int:pk>/',         views.verify_application,   name='admin_verify_application'),

    # User Management
    path('users/',                              views.user_list,            name='admin_user_list'),
    path('users/<int:pk>/toggle/',              views.user_toggle,          name='admin_user_toggle'),

    # Shift Management
    path('shifts/',                             views.shift_list,           name='admin_shift_list'),
    path('shifts/<int:pk>/deactivate/',         views.shift_deactivate,     name='admin_shift_deactivate'),

    # Vacancy Management
    path('vacancies/',                          views.vacancy_list,         name='admin_vacancy_list'),
    path('vacancies/<int:pk>/deactivate/',      views.vacancy_deactivate,   name='admin_vacancy_deactivate'),

    # Reports
    path('reports/',                            views.reports,              name='admin_reports'),

    path('get-cities/', views.get_cities, name='get_cities'),
    path('cities/', views.admin_city_list, name='admin_city_list'),
path('cities/add/', views.admin_city_add, name='admin_city_add'),
path('cities/delete/<int:pk>/', views.admin_city_delete, name='admin_city_delete'),

]