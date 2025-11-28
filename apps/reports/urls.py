from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReportTemplateViewSet, GeneratedReportViewSet, DashboardViewSet, DashboardWidgetViewSet,
    AuditReportsAPIView, FinancialReportsAPIView, audit_summary_data, financial_summary_data
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'templates', ReportTemplateViewSet, basename='report-template')
router.register(r'generated', GeneratedReportViewSet, basename='generated-report')
router.register(r'dashboards', DashboardViewSet, basename='dashboard')
router.register(r'widgets', DashboardWidgetViewSet, basename='dashboard-widget')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Specific report endpoints
    path('audit-reports/', AuditReportsAPIView.as_view(), name='audit-reports'),
    path('financial-reports/', FinancialReportsAPIView.as_view(), name='financial-reports'),
    
    # Summary data endpoints for dashboard widgets
    path('audit-summary/', audit_summary_data, name='audit-summary'),
    path('financial-summary/', financial_summary_data, name='financial-summary'),
]