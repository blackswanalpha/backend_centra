"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

# Import viewsets and views
from apps.clients.views import (
    ClientViewSet, ClientContactViewSet, IntakeLinkViewSet, IntakeSubmissionViewSet,
    validate_intake_access_code, submit_intake_form
)
from apps.employees.views import (
    EmployeeViewSet, DepartmentViewSet, PositionViewSet, EmployeeSkillViewSet, 
    TimeSheetViewSet, PerformanceReviewViewSet, auditor_availability_view
)
from apps.business_development.views import (
    LeadViewSet, OpportunityViewSet, ProposalViewSet, ContractViewSet, ActivityLogViewSet, ContractTemplateViewSet
)

# Create router for API endpoints
router = DefaultRouter()

# Register client-related viewsets
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'client-contacts', ClientContactViewSet, basename='client-contact')
router.register(r'intake-links', IntakeLinkViewSet, basename='intake-link')
router.register(r'intake-submissions', IntakeSubmissionViewSet, basename='intake-submission')

# Register employee-related viewsets
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'employee-skills', EmployeeSkillViewSet, basename='employee-skill')
router.register(r'timesheets', TimeSheetViewSet, basename='timesheet')
router.register(r'performance-reviews', PerformanceReviewViewSet, basename='performance-review')

# Register business development viewsets
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'opportunities', OpportunityViewSet, basename='opportunity')
router.register(r'proposals', ProposalViewSet, basename='proposal')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'contract-templates', ContractTemplateViewSet, basename='contract-template')
router.register(r'activities', ActivityLogViewSet, basename='activity')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/templates/', include('apps.templates.urls')), # New: include templates app URLs
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/', include('apps.certifications.urls')),
    path('api/v1/', include('apps.audits.urls')),
    path('api/v1/', include('apps.tasks.urls')),
    path('api/v1/', include('apps.finance.urls')),
    path('api/v1/', include('apps.dashboard.urls')),
    path('api/v1/consulting/', include('apps.consulting.urls')),
    path('api/v1/', include('apps.documents.urls')),
    path('api/v1/job-pipeline/', include('apps.job_pipeline.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    # Intake form public endpoints
    path('api/v1/clients/intake/validate/', validate_intake_access_code, name='intake-validate'),
    path('api/v1/clients/intake/<str:token>/submit/', submit_intake_form, name='intake-submit'),
    # Auditor availability endpoint
    path('api/v1/auditors/availability/', auditor_availability_view, name='auditor-availability'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
