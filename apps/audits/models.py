import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from apps.clients.models import Client


class ISOStandard(models.Model):
    code = models.CharField(max_length=20, unique=True)  # e.g., 'ISO 9001:2015'
    name = models.CharField(max_length=255)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    default_template = models.ForeignKey(
        'AuditChecklist',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_for_standards',
        help_text="Default audit template for this standard"
    )
    
    class Meta:
        db_table = 'iso_standards'
        ordering = ['code']
        
    def __str__(self):
        return f"{self.code} - {self.name}"


class Audit(models.Model):
    AUDIT_TYPES = [
        ('INITIAL', 'Initial Certification'),
        ('SURVEILLANCE_1', '1st Surveillance'),
        ('SURVEILLANCE_2', '2nd Surveillance'),
        ('RECERTIFICATION', 'Recertification'),
        ('SPECIAL', 'Special Audit'),
    ]
    
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('ON_HOLD', 'On Hold'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='audits')
    iso_standard = models.ForeignKey(ISOStandard, on_delete=models.CASCADE)
    pipeline = models.ForeignKey('job_pipeline.JobPipeline', on_delete=models.SET_NULL, null=True, blank=True, related_name='audits')
    audit_type = models.CharField(max_length=20, choices=AUDIT_TYPES)
    
    # Audit Details
    audit_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scope = models.TextField()
    
    # Schedule
    planned_start_date = models.DateField()
    planned_end_date = models.DateField()
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Assignment
    lead_auditor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audits_lead')
    auditors = models.ManyToManyField(User, related_name='audits_assigned', blank=True)
    
    # Template Association
    audit_template = models.ForeignKey('AuditChecklist', on_delete=models.SET_NULL, null=True, blank=True, related_name='audits')
    # Many-to-many relationship for multiple templates (certification standards)
    audit_templates = models.ManyToManyField('AuditChecklist', related_name='audits_multi', blank=True)
    
    # Status & Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    findings_count = models.PositiveIntegerField(default=0)
    major_findings = models.PositiveIntegerField(default=0)
    minor_findings = models.PositiveIntegerField(default=0)
    opportunities = models.PositiveIntegerField(default=0)
    
    # Certificate Information
    certificate_number = models.CharField(max_length=100, blank=True)
    certificate_issue_date = models.DateField(null=True, blank=True)
    certificate_expiry_date = models.DateField(null=True, blank=True)
    
    # System Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audits_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'audits'
        ordering = ['-planned_start_date']
        
    def __str__(self):
        return f"{self.audit_number} - {self.client.name}"


class AuditFinding(models.Model):
    FINDING_TYPES = [
        ('MAJOR', 'Major Non-Conformity'),
        ('MINOR', 'Minor Non-Conformity'),
        ('OPPORTUNITY', 'Opportunity for Improvement'),
        ('OBSERVATION', 'Observation'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('CLOSED', 'Closed'),
        ('VERIFIED', 'Verified'),
    ]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='findings')
    finding_number = models.CharField(max_length=50)
    finding_type = models.CharField(max_length=20, choices=FINDING_TYPES)
    
    # Finding Details
    clause_reference = models.CharField(max_length=100)  # ISO clause reference
    description = models.TextField()
    evidence = models.TextField()
    requirement = models.TextField()
    
    # Correction & Corrective Action
    correction = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)
    
    # Timeline
    target_date = models.DateField(null=True, blank=True)
    actual_closure_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    # Assignment
    responsible_person = models.CharField(max_length=255, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'audit_findings'
        ordering = ['finding_number']
        
    def __str__(self):
        return f"{self.finding_number} - {self.finding_type}"


def template_logo_path(instance, filename):
    """Generate upload path for template logos"""
    ext = filename.split('.')[-1]
    filename = f"template_{instance.id}_logo_{uuid.uuid4().hex[:8]}.{ext}"
    return f'template_logos/{filename}'


class AuditChecklist(models.Model):
    iso_standard = models.ForeignKey(ISOStandard, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_template = models.BooleanField(default=True)
    
    # Enhanced template features
    logo = models.ImageField(
        upload_to=template_logo_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'svg'])],
        help_text="Logo image for template header"
    )
    company_name = models.CharField(max_length=255, blank=True)
    header_content = models.TextField(blank=True, help_text="Header content for template")
    footer_content = models.TextField(blank=True, help_text="Footer content for template")
    
    # PDF styling options
    primary_color = models.CharField(max_length=7, default='#2563eb', help_text="Hex color code")
    include_compliance_checkboxes = models.BooleanField(default=True)
    enable_comments = models.BooleanField(default=True)
    enable_notes = models.BooleanField(default=True)
    enable_actions = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'audit_checklists'
        
    def __str__(self):
        return f"{self.title} - {self.iso_standard.code}"


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


class ChecklistItem(models.Model):
    ITEM_TYPES = [
        ('REQUIREMENT', 'Requirement'),
        ('PROCESS', 'Process'),
        ('DOCUMENT', 'Document'),
        ('RECORD', 'Record'),
        ('OBSERVATION', 'Observation'),
        ('CONTROL', 'Control'),
    ]

    checklist = models.ForeignKey(AuditChecklist, on_delete=models.CASCADE, related_name='items')
    section = models.ForeignKey(ChecklistSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    clause_reference = models.CharField(max_length=100)
    iso_clause = models.CharField(max_length=50, blank=True, help_text="ISO standard clause reference")
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    question = models.TextField()
    guidance = models.TextField(blank=True)
    
    # Enhanced features for auditor interaction
    actions_required = models.TextField(blank=True, help_text="Actions required for this item")
    allow_comments = models.BooleanField(default=True)
    allow_notes = models.BooleanField(default=True)
    allow_evidence_upload = models.BooleanField(default=True)
    
    # Organizational fields
    section_name = models.CharField(max_length=255, blank=True)
    subsection = models.CharField(max_length=255, blank=True)
    is_mandatory = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'checklist_items'
        ordering = ['order']
        
    def __str__(self):
        return f"{self.clause_reference} - {self.question[:50]}"


def evidence_upload_path(instance, filename):
    """Generate upload path for evidence files"""
    return f'audit_evidence/{instance.response.audit.audit_number}/{instance.response.checklist_item.clause_reference}/{filename}'


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
    checklist_item = models.ForeignKey(ChecklistItem, on_delete=models.CASCADE)
    
    # Response Data
    compliance_status = models.CharField(max_length=20, choices=COMPLIANCE_CHOICES, null=True, blank=True)
    
    # Evidence and Notes
    auditor_comments = models.TextField(blank=True)
    auditor_notes = models.TextField(blank=True)
    actions_taken = models.TextField(blank=True)
    evidence_description = models.TextField(blank=True)
    corrective_action_required = models.BooleanField(default=False)
    
    # Tracking
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['audit', 'checklist_item']
        db_table = 'audit_checklist_responses'
        
    def __str__(self):
        return f"{self.audit.audit_number} - {self.checklist_item.clause_reference}"


class ChecklistEvidence(models.Model):
    """Model for storing evidence files related to checklist responses"""

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


def audit_document_upload_path(instance, filename):
    """Generate upload path for audit documents"""
    return f'audit_documents/{instance.audit.id}/{filename}'


class AuditDocument(models.Model):
    """Model for storing general documents related to audits"""

    DOCUMENT_CATEGORIES = [
        ('GENERAL', 'General'),
        ('EVIDENCE', 'Evidence'),
        ('REPORT', 'Report'),
        ('CERTIFICATE', 'Certificate'),
        ('CORRESPONDENCE', 'Correspondence'),
        ('OTHER', 'Other'),
    ]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(
        upload_to=audit_document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xlsx', 'xls', 'txt'])],
        help_text="Supported formats: PDF, DOC, DOCX, JPG, JPEG, PNG, XLSX, XLS, TXT"
    )
    filename = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=DOCUMENT_CATEGORIES, default='GENERAL')
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_audit_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.audit.audit_number} - {self.filename}"