from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet,
    FolderViewSet,
    DocumentCategoryViewSet,
    DocumentAccessViewSet
)

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'categories', DocumentCategoryViewSet, basename='document-category')
router.register(r'access', DocumentAccessViewSet, basename='document-access')

urlpatterns = [
    path('', include(router.urls)),
]
