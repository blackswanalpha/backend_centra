from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CertificationViewSet, CertificateTemplateViewSet, public_certification_search

# Create router and register viewsets
router = DefaultRouter()
router.register(r'certifications', CertificationViewSet, basename='certification')
router.register(r'certificate-templates', CertificateTemplateViewSet, basename='certificate-template')

urlpatterns = [
    path('', include(router.urls)),
    # Public search endpoint (no authentication required)
    path('certifications/public/search/', public_certification_search, name='public-certification-search'),
]

