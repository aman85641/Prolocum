
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',        include('users.urls')),
    path('doctors/', include('doctors.urls')),
    path('nurses/', include('nurses.urls')),
    path('hospitals/', include('hospitals.urls')),
    path('adminpanel/', include('admin_panel.urls')),
    path('plans/', include('plans.urls')),
    path('shifts/', include('shifts.urls')),  # ✅ BAS YEH ADD KARO
    path('manifest.json', TemplateView.as_view(template_name='pwa/manifest.json', content_type='application/json'), name='manifest'),
    path('serviceworker.js', TemplateView.as_view(template_name='pwa/serviceworker.js', content_type='application/javascript'), name='serviceworker'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)