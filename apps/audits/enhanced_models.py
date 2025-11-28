"""
Enhanced audit models to support the new checklist functionality
This file contains the new models that need to be added to models.py
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from .models import Audit, AuditChecklist


# Enhanced Checklist Models
class ChecklistSection(models.Model):
    """Model to organize checklist items into sections"""
    checklist = models.ForeignKey(AuditChecklist, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'checklist_sections'
        ordering = ['order']
        
    def __str__(self):
        return f"{self.checklist.title} - {self.name}"


class EnhancedChecklistItem(models.Model):
    """Enhanced checklist item with additional fields"""
    ITEM_TYPES = [
        ('REQUIREMENT', 'Requirement'),
        ('PROCESS', 'Process'),
        ('DOCUMENT', 'Document'),
        ('RECORD', 'Record'),
        ('OBSERVATION', 'Observation'),
        ('CONTROL', 'Control'),
    ]

    ANSWER_TYPES = [
        ('COMPLIANCE', 'Compliance (Compliant/Non-Compliant/N/A)'),
        ('YES_NO', 'Yes/No'),
        ('TEXT', 'Text Response'),
        ('NUMERIC', 'Numeric Value'),
        ('EVIDENCE', 'Evidence Upload'),
        ('CHECKLIST', 'Sub-checklist'),
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('RATING', 'Rating Scale'),
    ]

    # Basic Information
    checklist = models.ForeignKey(AuditChecklist, on_delete=models.CASCADE, related_name='enhanced_items')
    section = models.ForeignKey(ChecklistSection, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Core Question Data
    clause_reference = models.CharField(max_length=100)
    iso_clause = models.CharField(max_length=50, help_text="ISO standard clause reference")
    question = models.TextField()
    guidance = models.TextField(blank=True)
    
    # Categorization
    section_name = models.CharField(max_length=255, blank=True)
    subsection = models.CharField(max_length=255, blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    answer_type = models.CharField(max_length=20, choices=ANSWER_TYPES, default='COMPLIANCE')
    
    # Enhanced Features
    actions_required = models.TextField(blank=True, help_text="Actions required for this item")
    auditor_instructions = models.TextField(blank=True, help_text="Instructions for auditors")
    
    # Configuration
    is_mandatory = models.BooleanField(default=True)
    allows_comments = models.BooleanField(default=True)
    allows_notes = models.BooleanField(default=True)
    allows_evidence = models.BooleanField(default=True)
    multiple_choice_options = models.JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enhanced_checklist_items'
        ordering = ['order', 'clause_reference']
        
    def __str__(self):
        return f"{self.clause_reference} - {self.question[:50]}"


class AuditChecklistResponse(models.Model):
    """Model to store audit-specific checklist responses"""
    
    COMPLIANCE_CHOICES = [
        ('compliant', 'Compliant'),
        ('needs_improvement', 'Needs Improvement'),
        ('non_compliant', 'Non-Compliant'),
        ('not_applicable', 'Not Applicable'),
        ('pending', 'Pending Review'),
    ]

    # Relationships
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='checklist_responses')
    checklist_item = models.ForeignKey(EnhancedChecklistItem, on_delete=models.CASCADE)
    
    # Response Data
    compliance_status = models.CharField(max_length=20, choices=COMPLIANCE_CHOICES, null=True, blank=True)
    text_response = models.TextField(blank=True)
    numeric_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    yes_no_response = models.BooleanField(null=True, blank=True)
    multiple_choice_response = models.JSONField(default=list, blank=True)
    rating_value = models.PositiveIntegerField(null=True, blank=True)
    
    # Evidence and Notes
    evidence_description = models.TextField(blank=True)
    auditor_comments = models.TextField(blank=True)
    auditor_notes = models.TextField(blank=True)
    actions_taken = models.TextField(blank=True)
    corrective_action_required = models.BooleanField(default=False)
    
    # Tracking
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_responses')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['audit', 'checklist_item']
        db_table = 'audit_checklist_responses'
        
    def __str__(self):
        return f"{self.audit.audit_number} - {self.checklist_item.clause_reference}"


class ChecklistEvidence(models.Model):
    """Model for storing evidence files related to checklist responses"""
    
    def evidence_upload_path(instance, filename):
        return f'audit_evidence/{instance.response.audit.audit_number}/{instance.response.checklist_item.clause_reference}/{filename}'
    
    response = models.ForeignKey(AuditChecklistResponse, on_delete=models.CASCADE, related_name='evidence_files')
    file = models.FileField(
        upload_to=evidence_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xlsx', 'xls'])],
        help_text="Supported formats: PDF, DOC, DOCX, JPG, JPEG, PNG, XLSX, XLS"
    )
    filename = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'checklist_evidence'
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"{self.response.audit.audit_number} - {self.filename}"


# Template Enhancement Models
class TemplateSection(models.Model):
    """Model for organizing template content into sections"""
    SECTION_TYPES = [
        ('header', 'Header Section'),
        ('title_page', 'Title Page'),
        ('guidance', 'Guidance Notes'),
        ('scope', 'Audit Scope'),
        ('objectives', 'Audit Objectives'), 
        ('checklist', 'Checklist Items'),
        ('recommendations', 'Recommendations'),
        ('sign_off', 'Sign-off Section'),
        ('footer', 'Footer Section'),
    ]
    
    template = models.ForeignKey(AuditChecklist, on_delete=models.CASCADE, related_name='template_sections')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    name = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'template_sections'
        ordering = ['order']
        
    def __str__(self):
        return f"{self.template.title} - {self.name}"


def template_logo_path(instance, filename):
    """Generate upload path for template logos"""
    ext = filename.split('.')[-1]
    filename = f"template_{instance.template.id}_logo_{uuid.uuid4().hex[:8]}.{ext}"
    return f'template_logos/{filename}'


class TemplateCustomization(models.Model):
    """Model for template customization settings"""
    template = models.OneToOneField(AuditChecklist, on_delete=models.CASCADE, related_name='customization')
    
    # Logo and Branding
    logo = models.ImageField(
        upload_to=template_logo_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'svg'])],
        help_text="Logo image for template header"
    )
    company_name = models.CharField(max_length=255, blank=True)
    company_address = models.TextField(blank=True)
    
    # Styling Options
    primary_color = models.CharField(max_length=7, default='#2563eb', help_text="Hex color code")
    secondary_color = models.CharField(max_length=7, default='#64748b', help_text="Hex color code")
    font_family = models.CharField(max_length=50, default='Arial', help_text="Font family name")
    
    # Header/Footer Content
    header_text = models.TextField(blank=True)
    footer_text = models.TextField(blank=True)
    
    # PDF Settings
    page_size = models.CharField(max_length=10, default='A4', choices=[('A4', 'A4'), ('Letter', 'Letter')])
    include_page_numbers = models.BooleanField(default=True)
    include_watermark = models.BooleanField(default=False)
    watermark_text = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'template_customizations'
        
    def __str__(self):
        return f"{self.template.title} - Customization"


# Progress Tracking Models
class AuditChecklistProgress(models.Model):
    """Model to track checklist completion progress"""
    audit = models.OneToOneField(Audit, on_delete=models.CASCADE, related_name='checklist_progress')
    checklist = models.ForeignKey(AuditChecklist, on_delete=models.CASCADE)
    
    # Progress Metrics
    total_items = models.PositiveIntegerField(default=0)
    completed_items = models.PositiveIntegerField(default=0)
    mandatory_items = models.PositiveIntegerField(default=0)
    mandatory_completed = models.PositiveIntegerField(default=0)
    
    # Compliance Summary
    compliant_items = models.PositiveIntegerField(default=0)
    non_compliant_items = models.PositiveIntegerField(default=0)
    needs_improvement_items = models.PositiveIntegerField(default=0)
    not_applicable_items = models.PositiveIntegerField(default=0)
    
    # Status
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'audit_checklist_progress'
        
    def __str__(self):
        return f"{self.audit.audit_number} - {self.completion_percentage}% Complete"


class ChecklistComment(models.Model):
    """Model for comments on checklist items"""
    COMMENT_TYPES = [
        ('auditor', 'Auditor Comment'),
        ('reviewer', 'Reviewer Comment'),
        ('client', 'Client Response'),
        ('follow_up', 'Follow-up Note'),
    ]
    
    response = models.ForeignKey(AuditChecklistResponse, on_delete=models.CASCADE, related_name='comments')
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES, default='auditor')
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'checklist_comments'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.response.audit.audit_number} - {self.comment_type} comment"