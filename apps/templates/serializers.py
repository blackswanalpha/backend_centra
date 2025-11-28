# backend_centra/apps/templates/serializers.py
from rest_framework import serializers
from .models import Template

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = '__all__'

    def create(self, validated_data):
        return super().create(validated_data)
