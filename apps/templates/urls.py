# backend_centra/apps/templates/urls.py
from rest_framework.routers import DefaultRouter
from .views import TemplateViewSet

router = DefaultRouter()
router.register(r'', TemplateViewSet, basename='template')

urlpatterns = router.urls
