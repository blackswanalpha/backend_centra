from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator, RegexValidator, MinValueValidator, MaxValueValidator
import secrets
import random
import string


class Client(models.Model):
    """
    Client model that matches the frontend interface requirements.
    Maps frontend fields to backend database fields.
    """

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('at-risk', 'At Risk'),
        ('churned', 'Churned'),
    ]

    CERTIFICATION_CHOICES = [
        ('ISO 9001:2015', 'ISO 9001:2015'),
        ('ISO 14001:2015', 'ISO 14001:2015'),
        ('ISO 45001:2018', 'ISO 45001:2018'),
        ('ISO 27001:2013', 'ISO 27001:2013'),
        ('ISO 22000:2018', 'ISO 22000:2018'),
    ]

    CURRENCY_CHOICES = [
        ('GBP', 'British Pound'),
        ('USD', 'US Dollar'),
        ('KES', 'Kenyan Shilling'),
        ('EUR', 'Euro'),
        ('TZS', 'Tanzanian Shilling'),
        ('UGX', 'Ugandan Shilling'),
    ]

    # Basic Information (Required fields from frontend)
    name = models.CharField(max_length=255, help_text="Client/Company name")
    contact = models.CharField(max_length=255, help_text="Primary contact person name")
    email = models.EmailField(validators=[EmailValidator()], help_text="Primary contact email")
    phone = models.CharField(max_length=50, help_text="Primary contact phone")
    address = models.TextField(help_text="Primary address")

    # Site Information (Optional fields from frontend)
    site_contact = models.CharField(max_length=255, blank=True, null=True, help_text="Site contact person")
    site_phone = models.CharField(max_length=50, blank=True, null=True, help_text="Site phone number")

    # Billing Information (from Contacts sheet)
    currency_code = models.CharField(max_length=10, choices=CURRENCY_CHOICES, blank=True, null=True, help_text="Currency code for billing")
    billing_attention = models.CharField(max_length=255, blank=True, null=True, help_text="Contact person for billing")
    billing_address = models.TextField(blank=True, null=True, help_text="Billing address line 1")
    billing_street2 = models.CharField(max_length=255, blank=True, null=True, help_text="Billing address line 2")
    billing_city = models.CharField(max_length=100, blank=True, null=True, help_text="Billing city")
    billing_state = models.CharField(max_length=100, blank=True, null=True, help_text="Billing state/province")
    billing_country = models.CharField(max_length=100, blank=True, null=True, help_text="Billing country")
    payment_terms = models.CharField(max_length=255, blank=True, null=True, help_text="Payment terms")

    # Physical Location (from Project sheet)
    physical_address = models.TextField(blank=True, null=True, help_text="Physical location address")
    city = models.CharField(max_length=100, blank=True, null=True, help_text="Physical city")
    country = models.CharField(max_length=100, blank=True, null=True, help_text="Physical country")

    # Status & Business Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    industry = models.CharField(max_length=100, blank=True, null=True)

    # Project/Certification Information (from Project sheet)
    project_ref = models.CharField(max_length=50, blank=True, null=True, help_text="Project reference number")
    scope_of_certification = models.TextField(blank=True, null=True, help_text="Detailed scope of certification")
    certificate_no = models.CharField(max_length=50, blank=True, null=True, help_text="Certificate number")
    registration_date = models.DateField(blank=True, null=True, help_text="Initial registration date")
    certificate_date = models.DateField(blank=True, null=True, help_text="Current certificate issue date")
    expiry_date = models.DateField(blank=True, null=True, help_text="Certificate expiry date")

    # Certifications (stored as JSON array)
    certifications = models.JSONField(default=list, blank=True, help_text="List of certification standards")

    # Health Score (0-100)
    health_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Client health score (0-100)"
    )

    # Audit Dates
    last_audit_date = models.DateField(null=True, blank=True)
    next_audit_date = models.DateField(null=True, blank=True)

    # System Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clients_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clients'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ClientContact(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(max_length=20, blank=True)
    is_primary = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client_contacts'
        
    def __str__(self):
        return f"{self.name} - {self.client.name}"


class IntakeLink(models.Model):
    # Basic Information
    title = models.CharField(max_length=255, blank=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    access_code = models.CharField(max_length=16)
    description = models.TextField(blank=True)

    # Status and Limits
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    max_uses = models.PositiveIntegerField(default=1)
    current_uses = models.PositiveIntegerField(default=0)

    # Related Entities (optional)
    related_audit_id = models.CharField(max_length=255, blank=True, null=True)
    related_project_id = models.CharField(max_length=255, blank=True, null=True)

    # Metadata
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Tracking
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'intake_links'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['is_active', 'expires_at']),
        ]

    def __str__(self):
        return self.title or f"Link {self.token[:8]}..."

    def save(self, *args, **kwargs):
        """Auto-generate token and access_code if not provided."""
        if not self.token:
            self.token = secrets.token_urlsafe(48)

        if not self.access_code:
            # Generate access code in format: XXXX-XXXX
            part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.access_code = f"{part1}-{part2}"

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if the link has expired based on time."""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_exhausted(self):
        """Check if the link has been used up to its maximum uses."""
        return self.current_uses >= self.max_uses

    @property
    def is_usable(self):
        """Check if the link can still be used (active, not expired, not exhausted)."""
        return self.is_active and not self.is_expired and not self.is_exhausted

    @property
    def status(self):
        """
        Get the current status of the intake link.
        Returns: 'active', 'expired', 'exhausted', or 'inactive'
        """
        if not self.is_active:
            return 'inactive'
        elif self.is_expired:
            return 'expired'
        elif self.is_exhausted:
            return 'exhausted'
        else:
            return 'active'

    @property
    def status_display(self):
        """Get a human-readable status display."""
        status_map = {
            'active': 'Active',
            'expired': 'Expired',
            'exhausted': 'Exhausted (Max Uses Reached)',
            'inactive': 'Inactive'
        }
        return status_map.get(self.status, 'Unknown')


class IntakeSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # Link and Client
    intake_link = models.ForeignKey(IntakeLink, on_delete=models.CASCADE, related_name='submissions')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='intake_submissions')

    # Submission Data
    client_data = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Request Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Review Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    # Legacy field for backward compatibility
    processed = models.BooleanField(default=False)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_submissions')
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'intake_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', 'submitted_at']),
            models.Index(fields=['intake_link', 'submitted_at']),
        ]

    def __str__(self):
        company_name = self.client_data.get('name', 'Unknown')
        return f"Submission: {company_name} - {self.submitted_at.strftime('%Y-%m-%d')}"