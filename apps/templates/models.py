# backend_centra/apps/templates/models.py
from django.db import models
from django.utils import timezone

class Template(models.Model):
    id = models.CharField(max_length=255, primary_key=True, unique=True) # Frontend-generated ID or UUID
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, default='audit') # e.g., 'audit', 'contract', 'report', 'certification'
    pages = models.JSONField(default=list) # Store list of TemplatePage objects as JSON
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    settings = models.JSONField(default=dict) # Store TemplateSettings as JSON
    metadata = models.JSONField(default=dict, blank=True, null=True) # Store metadata as JSON

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title