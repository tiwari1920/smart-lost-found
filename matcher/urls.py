from django.urls import path

from . import views

urlpatterns = [
    path('item/<int:pk>/', views.item_matches, name='item_matches'),
]