from django.urls import path

from . import views
app_name = 'notifications'
urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('read/', views.mark_all_read, name='mark_all_read'),
]