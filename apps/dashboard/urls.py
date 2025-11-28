"""
Dashboard URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/overview/', views.overview_dashboard, name='dashboard-overview'),
    path('dashboard/financial/', views.financial_dashboard, name='dashboard-financial'),
    path('dashboard/sales/', views.sales_dashboard, name='dashboard-sales'),
    path('dashboard/auditors/', views.auditor_dashboard, name='dashboard-auditors'),
    path('dashboard/clients/', views.client_dashboard, name='dashboard-clients'),
    path('dashboard/operations/', views.operations_dashboard, name='dashboard-operations'),
    path('dashboard/activity/', views.activity_dashboard, name='dashboard-activity'),
    path('dashboard/goals/', views.goals_dashboard, name='dashboard-goals'),
]

