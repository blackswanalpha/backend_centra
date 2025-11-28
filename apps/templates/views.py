# backend_centra/apps/templates/views.py
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Template
from .serializers import TemplateSerializer

class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    lookup_field = 'id' # Use the 'id' field for lookups
    permission_classes = [AllowAny] # Temporarily allow any access