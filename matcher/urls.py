from django.urls import path

from . import views

urlpatterns = [
    path('item/<int:pk>/', views.item_matches, name='item_matches'),
    path('claims/', views.claims, name='claims'),
    path('claim/start/<int:lost_pk>/<int:found_pk>/', views.claim_start, name='claim_start'),
    path('claim/<int:pk>/', views.claim_detail, name='claim_detail'),
    path('claim/<int:pk>/action/', views.claim_action, name='claim_action'),
]