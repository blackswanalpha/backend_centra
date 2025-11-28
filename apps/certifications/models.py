from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from apps.clients.models import Client
from apps.audits.models import ISOStandard, Audit
import uuid
import os


def certificate_template_path(instance, filename):
    """Generate upload path for certificate templates."""
    ext = filename.split('.')[-1]
    filename = f"{instance.name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('certificate_templates', filename)


def generated_certificate_path(instance, filename):
    """Generate upload path for generated certificates."""
    from datetime import datetime
    now = datetime.now()
    ext = filename.split('.')[-1]
    filename = f"{instance.certificate_number}.{ext}"
    return os.path.join('certificates', str(now.year), str(now.month).zfill(2), filename)


class CertificateTemplate(models.Model):
    """
    Model for storing certificate templates.
    Supports multiple template types (JasperReports, DOCX, PDF).
    """
    TEMPLATE_TYPES = [
        ('jasper', 'JasperReports (.jrxml)'),
        ('docx', 'Microsoft Word (.docx)'),
        ('pdf', 'PDF Template'),
        ('html', 'HTML Template'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Template name")
    description = models.TextField(blank=True, help_text="Template description")

    # Template Configuration
    iso_standard = models.ForeignKey(
        ISOStandard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="ISO standard this template is for (null for generic templates)"
    )
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, default='docx')
    template_file = models.FileField(
        upload_to=certificate_template_path,
        validators=[FileExtensionValidator(allowed_extensions=['jrxml', 'docx', 'pdf', 'html'])],
        help_text="Template file"
    )

    # Template Variables (JSON schema defining available variables)
    variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="Template variable definitions and default values"
    )

    # Status
    is_active = models.BooleanField(default=True, help_text="Is this template active?")
    is_default = models.BooleanField(
        default=False,
        help_text="Is this the default template for its ISO standard?"
    )

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='templates_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificate_templates'
        ordering = ['-created_at']
        unique_together = [['iso_standard', 'is_default']]  # Only one default per standard

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class Certification(models.Model):
    """
    Model for storing client certifications.
    Tracks certification lifecycle from issuance to expiry.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expiring-soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core Relationships
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='issued_certifications')
    iso_standard = models.ForeignKey(ISOStandard, on_delete=models.PROTECT)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certifications',
        help_text="The audit that resulted in this certification"
    )

    # Certificate Details
    certificate_number = models.CharField(max_length=100, unique=True, help_text="Unique certificate number")
    issue_date = models.DateField(help_text="Date certificate was issued")
    expiry_date = models.DateField(help_text="Date certificate expires")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Scope & Details
    scope = models.TextField(help_text="Certification scope")

    # Auditor Information
    lead_auditor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certifications_audited'
    )

    # Certification Body Information
    certification_body = models.CharField(max_length=255, blank=True, help_text="Name of certification body")
    accreditation_number = models.CharField(max_length=100, blank=True, help_text="Accreditation number")

    # Template & Document
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certifications'
    )
    document_url = models.FileField(
        upload_to=generated_certificate_path,
        blank=True,
        null=True,
        help_text="Generated certificate document"
    )

    # Additional Data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional certification metadata"
    )
    notes = models.TextField(blank=True, help_text="Internal notes")

    # System Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='certifications_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certifications'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['status', 'expiry_date']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['certificate_number']),
        ]

    def __str__(self):
        return f"{self.certificate_number} - {self.client.name} ({self.iso_standard.code})"

    def save(self, *args, **kwargs):
        """Auto-update status based on expiry date."""
        from datetime import date, timedelta

        if self.expiry_date:
            today = date.today()
            days_until_expiry = (self.expiry_date - today).days

            # Auto-update status based on expiry
            if self.status not in ['suspended', 'revoked']:
                if days_until_expiry < 0:
                    self.status = 'expired'
                elif days_until_expiry <= 90:  # 3 months
                    self.status = 'expiring-soon'
                elif self.status == 'pending':
                    pass  # Keep pending status
                else:
                    self.status = 'active'

        super().save(*args, **kwargs)

    @property
    def days_until_expiry(self):
        """Calculate days until expiry."""
        from datetime import date
        if self.expiry_date:
            return (self.expiry_date - date.today()).days
        return None

    @property
    def is_expired(self):
        """Check if certification is expired."""
        from datetime import date
        return self.expiry_date < date.today() if self.expiry_date else False

    @property
    def is_expiring_soon(self):
        """Check if certification is expiring within 90 days."""
        days = self.days_until_expiry
        return 0 <= days <= 90 if days is not None else False


class CertificationHistory(models.Model):
    """
    Model for tracking certification history and status changes.
    Provides audit trail for all certification actions.
    """
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('issued', 'Issued'),
        ('renewed', 'Renewed'),
        ('suspended', 'Suspended'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
        ('reactivated', 'Reactivated'),
        ('updated', 'Updated'),
        ('document_generated', 'Document Generated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    certification = models.ForeignKey(Certification, on_delete=models.CASCADE, related_name='history')

    # Action Details
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    previous_status = models.CharField(max_length=20, blank=True, help_text="Status before action")
    new_status = models.CharField(max_length=20, blank=True, help_text="Status after action")

    # Additional Information
    notes = models.TextField(blank=True, help_text="Notes about this action")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional action metadata"
    )

    # Tracking
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'certification_history'
        ordering = ['-timestamp']
        verbose_name_plural = 'Certification histories'

    def __str__(self):
        return f"{self.certification.certificate_number} - {self.get_action_display()} at {self.timestamp}"
