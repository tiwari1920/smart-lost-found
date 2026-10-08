from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

# Admin branding: replaces the default "Django administration"
admin.site.site_header = f'{settings.SITE_NAME} Administration'
admin.site.site_title = settings.SITE_TITLE
admin.site.index_title = 'Admin Dashboard'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('items/', include('items.urls')),
    path('matches/', include('matcher.urls')),
]

# While developing, let Django serve uploaded photos from /media/
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)