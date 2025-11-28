from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_overview, name='dashboard-overview'),
    path('dashboard/consultants/', views.consultant_performance, name='consultant-performance'),
    path('dashboard/clients/', views.client_health, name='client-health'),
    path('dashboard/delivery/', views.delivery_excellence, name='delivery-excellence'),
]
