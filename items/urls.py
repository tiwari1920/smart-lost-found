from django.urls import path

from . import views

urlpatterns = [
    path('report/lost/', views.report_lost, name='report_lost'),
        path('report/found/',views.report_found, name='report_found'),
    path('browse/', views.browse_items, name='browse_items'),
        path('mine/', views.my_reports, name='my_reports'),
    path('mine/', views.my_reports, name='my_reports'),
    path('<int:pk>/', views.item_detail, name='item_detail'),
    path('<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('<int:pk>/status/', views.item_change_status, name='item_change_status'),
]