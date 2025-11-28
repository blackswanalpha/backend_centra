from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuditViewSet, AuditFindingViewSet, ISOStandardViewSet, AuditChecklistViewSet,
    ChecklistSectionViewSet, AuditChecklistResponseViewSet, ChecklistEvidenceViewSet,
    AuditDocumentViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'audits', AuditViewSet, basename='audit')
router.register(r'audit-findings', AuditFindingViewSet, basename='audit-finding')
router.register(r'iso-standards', ISOStandardViewSet, basename='iso-standard')
router.register(r'audit-checklists', AuditChecklistViewSet, basename='audit-checklist')
router.register(r'checklist-sections', ChecklistSectionViewSet, basename='checklist-section')
router.register(r'audit-checklist-responses', AuditChecklistResponseViewSet, basename='audit-checklist-response')
router.register(r'checklist-evidence', ChecklistEvidenceViewSet, basename='checklist-evidence')
router.register(r'audit-documents', AuditDocumentViewSet, basename='audit-document')

urlpatterns = [
    path('', include(router.urls)),
]

