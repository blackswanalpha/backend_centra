from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client


class Lead(models.Model):
    SOURCE_CHOICES = [
        ('WEBSITE', 'Website'),
        ('REFERRAL', 'Referral'),
        ('COLD_CALL', 'Cold Call'),
        ('EMAIL', 'Email Campaign'),
        ('SOCIAL_MEDIA', 'Social Media'),
        ('EVENT', 'Event/Conference'),
        ('PARTNER', 'Partner'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('CONTACTED', 'Contacted'),
        ('QUALIFIED', 'Qualified'),
        ('PROPOSAL_SENT', 'Proposal Sent'),
        ('NEGOTIATION', 'Negotiation'),
        ('CONVERTED', 'Converted'),
        ('LOST', 'Lost'),
    ]

    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100, blank=True)
    
    # Lead Details
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    industry = models.CharField(max_length=100)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='KES')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    probability = models.PositiveIntegerField(default=0)  # 0-100%
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads_assigned')
    
    # Timeline
    first_contact_date = models.DateField(null=True, blank=True)
    last_contact_date = models.DateField(null=True, blank=True)
    expected_close_date = models.DateField(null=True, blank=True)
    
    # Conversion
    converted_to_client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    conversion_date = models.DateField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='leads_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.company_name} - {self.contact_person}"


class Opportunity(models.Model):
    STATUS_CHOICES = [
        ('PROSPECTING', 'Prospecting'),
        ('QUALIFICATION', 'Qualification'),
        ('PROPOSAL', 'Proposal'),
        ('NEGOTIATION', 'Negotiation'),
        ('CLOSED_WON', 'Closed Won'),
        ('CLOSED_LOST', 'Closed Lost'),
    ]
    
    SERVICE_TYPES = [
        ('ISO_CERTIFICATION', 'ISO Certification'),
        ('CONSULTING', 'Consulting'),
        ('TRAINING', 'Training'),
        ('AUDIT', 'Internal Audit'),
        ('COMPLIANCE', 'Compliance Review'),
        ('RISK_ASSESSMENT', 'Risk Assessment'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='opportunities')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Opportunity Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    
    # Financial
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    probability = models.PositiveIntegerField(default=0)  # 0-100%
    
    # Status & Timeline
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROSPECTING')
    expected_close_date = models.DateField()
    actual_close_date = models.DateField(null=True, blank=True)
    
    # Assignment
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='opportunities_owned')
    
    # Competition & Decision
    competitors = models.TextField(blank=True)
    decision_criteria = models.TextField(blank=True)
    decision_makers = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='opportunities_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'opportunities'
        ordering = ['-expected_close_date']
        
    def __str__(self):
        return f"{self.title} - {self.client.name}"


class Proposal(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('REVIEW', 'Under Review'),
        ('SENT', 'Sent'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='proposals')
    proposal_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    
    # Content
    executive_summary = models.TextField()
    scope_of_work = models.TextField()
    methodology = models.TextField()
    timeline = models.TextField()
    deliverables = models.TextField()
    
    # Financial
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    payment_terms = models.TextField()
    
    # Status & Timeline
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    prepared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='proposals_prepared')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='proposals_approved')
    
    sent_date = models.DateField(null=True, blank=True)
    response_deadline = models.DateField(null=True, blank=True)
    response_date = models.DateField(null=True, blank=True)
    
    # Files
    document_file = models.FileField(upload_to='proposals/', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'proposals'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.proposal_number} - {self.title}"


class ContractTemplate(models.Model):
    """
    Model to store contract templates created in the Template Builder
    Links the business development contracts with template builder templates
    """
    TEMPLATE_TYPES = [
        ('CERTIFICATION_CONTRACT', 'Certification Contract'),
        ('SERVICE_AGREEMENT', 'Service Agreement'),
        ('CONSULTING_AGREEMENT', 'Consulting Agreement'),
        ('NDA', 'Non-Disclosure Agreement'),
        ('SOW', 'Statement of Work'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]

    # Template Identification
    template_id = models.CharField(max_length=100, unique=True, help_text="ID from template builder")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES)
    
    # Template Content (JSON from template builder)
    template_data = models.JSONField(
        help_text="Complete template data from template builder including pages, sections, and metadata"
    )
    
    # Template Settings
    is_default = models.BooleanField(default=False, help_text="Is this the default template for this type?")
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Version Management
    version = models.CharField(max_length=20, default='1.0')
    parent_template = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='versions'
    )
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contract_templates_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contract_templates'
        ordering = ['-created_at']
        unique_together = ['template_type', 'version', 'is_default']
        
    def __str__(self):
        return f"{self.name} v{self.version}"


class Contract(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('UNDER_REVIEW', 'Under Review'),
        ('PENDING_SIGNATURE', 'Pending Signature'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('TERMINATED', 'Terminated'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    CONTRACT_TYPES = [
        ('SERVICE', 'Service Agreement'),
        ('CONSULTING', 'Consulting Agreement'),
        ('CERTIFICATION', 'Certification Agreement'),
        ('TRAINING', 'Training Agreement'),
        ('MAINTENANCE', 'Maintenance Agreement'),
    ]

    # Core Relationships - Link to Opportunity instead of Client
    proposal = models.ForeignKey(Proposal, on_delete=models.SET_NULL, null=True, blank=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='contracts', null=True, blank=True)
    
    # Template Integration - NEW: Link to contract template
    contract_template = models.ForeignKey(
        ContractTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='generated_contracts',
        help_text="Template used to generate this contract"
    )
    template_version_used = models.CharField(max_length=20, blank=True, help_text="Version of template used")
    
    # Contract Details
    contract_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPES)
    description = models.TextField()
    agreement_date = models.DateField(null=True, blank=True)
    
    # Client Contact Information (from opportunity/client)
    client_organization = models.CharField(max_length=255, default='')
    client_address = models.TextField(default='')
    client_contact_person = models.CharField(max_length=255, default='')
    client_telephone = models.CharField(max_length=50, blank=True)
    client_email = models.EmailField(default='contact@example.com')
    client_secondary_email = models.EmailField(blank=True)
    client_website = models.URLField(blank=True)
    site_covered = models.TextField(default='', help_text="Physical location/site covered by this contract")
    
    # Certification Body Information
    cb_name = models.CharField(max_length=255, default='AceQu International Limited')
    cb_address = models.TextField(default='168 City Road, Cardiff, Wales, CF24 3JE, United Kingdom')
    cb_role = models.TextField(default='Accredited Certification Body providing ISO certification audits')
    
    # Scope of Work - ISO Standards
    iso_standards = models.JSONField(
        default=list,
        help_text="List of ISO standards, e.g., ['ISO 9001:2015', 'ISO 14001:2015', 'ISO 45001:2018']"
    )
    scope_of_work = models.TextField(default='', help_text="Detailed scope of certification work")
    
    # Certification Process Details
    # Stage I Audit
    stage_1_audit_days = models.PositiveIntegerField(default=1, help_text="Stage I audit duration in days")
    stage_1_audit_description = models.TextField(
        default='Reviews documentation, readiness, and preparedness.',
        help_text="Description of Stage I audit process"
    )
    stage_1_remote_allowed = models.BooleanField(default=True, help_text="Can be on-site or remote")
    
    # Stage II Audit
    stage_2_audit_days = models.PositiveIntegerField(default=3, help_text="Stage II audit duration in days")
    stage_2_audit_description = models.TextField(
        default='Full assessment of implementation and conformity to standards. Subject to change based on growth.',
        help_text="Description of Stage II audit process"
    )
    
    # Surveillance Audits
    surveillance_audit_frequency = models.CharField(
        max_length=50,
        default='Annual',
        help_text="Frequency of surveillance audits (e.g., Annual, Semi-annual)"
    )
    surveillance_audit_description = models.TextField(
        default='Year 2 and Year 3 - Annual audits to verify ongoing conformity.',
        help_text="Description of surveillance audit process"
    )
    
    # Recertification Audit
    recertification_audit_timing = models.CharField(
        max_length=100,
        default='3 months before certificate expiry',
        help_text="When recertification audit is conducted"
    )
    recertification_audit_description = models.TextField(
        default='Man-days similar to Stage II unless changes occur.',
        help_text="Description of recertification audit process"
    )
    
    # Timeline & Certification Cycle
    start_date = models.DateField()
    end_date = models.DateField()
    duration_months = models.PositiveIntegerField(default=36, help_text="Contract duration in months")
    certification_cycle_years = models.PositiveIntegerField(default=3)
    stage_1_stage_2_max_gap_days = models.PositiveIntegerField(
        default=90,
        help_text="Stage I & Stage II must be completed within this many days of each other"
    )
    nc_closure_max_days = models.PositiveIntegerField(
        default=60,
        help_text="Non-conformities must be closed within this many days max"
    )
    certificate_issue_days = models.PositiveIntegerField(
        default=14,
        help_text="Certificates issued within this many working days after NC closure"
    )
    certificate_validity_years = models.PositiveIntegerField(
        default=3,
        help_text="Certificate validity in years, with mandatory annual surveillance audits"
    )
    certificate_validity_extension_allowed = models.BooleanField(
        default=False,
        help_text="Validity cannot be extended except through recertification"
    )
    
    # Fee Structure (per standard)
    fee_per_standard_year_1 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1000,
        help_text="Certification audit fee per standard (Year 1)"
    )
    fee_per_standard_year_2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1000,
        help_text="Surveillance audit fee per standard (Year 2)"
    )
    fee_per_standard_year_3 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1000,
        help_text="Surveillance audit fee per standard (Year 3)"
    )
    recertification_fee_tbd = models.BooleanField(
        default=True,
        help_text="Whether recertification fee is to be determined"
    )
    recertification_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Recertification audit fee (if determined)"
    )
    
    # Additional Fees
    additional_fees_description = models.TextField(
        default='Follow-up audits (closing NCs), Scope extensions, Major operational changes',
        blank=True,
        help_text="Description of additional fees that may apply"
    )
    
    # Total Financial
    contract_value = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_schedule = models.TextField(default='')
    
    # Cancellation & Rescheduling Policy
    cancellation_notice_days = models.PositiveIntegerField(
        default=15,
        help_text="Working days notice required for cancellation/rescheduling"
    )
    cancellation_fee_applies = models.BooleanField(
        default=True,
        help_text="Whether full audit fee applies for late cancellations"
    )
    
    # Confidentiality & Data Protection
    confidentiality_clause = models.TextField(
        default="AceQu will keep all client information confidential except when required by law or accreditation rules."
    )
    data_protection_compliance = models.TextField(
        default="AceQu must store and process data securely following GDPR and other applicable regulations."
    )
    
    # Client Responsibilities
    client_responsibilities = models.JSONField(
        default=list,
        help_text="List of client responsibilities and commitments"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Signatures
    client_signed_date = models.DateField(null=True, blank=True)
    company_signed_date = models.DateField(null=True, blank=True)
    signed_by_client_name = models.CharField(max_length=255, blank=True)
    signed_by_client_position = models.CharField(max_length=255, blank=True)
    signed_by_company = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts_signed'
    )
    signed_by_company_name = models.CharField(max_length=255, default='Kuldip Degon, PCQI')
    signed_by_company_position = models.CharField(max_length=255, default='Lead Auditor, AceQu International Ltd')
    
    # Files
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    
    # Termination & Renewal
    termination_notice_days = models.PositiveIntegerField(
        default=30,
        help_text="Either party may terminate with this many days written notice"
    )
    termination_fee_waiver = models.BooleanField(
        default=False,
        help_text="Termination does not waive fees for completed or confirmed audits"
    )
    auto_renewal = models.BooleanField(default=False)
    renewal_notice_days = models.PositiveIntegerField(default=30)
    
    # Entire Agreement Clause
    entire_agreement_clause = models.TextField(
        default='This is the entire agreement. Amendments must be in writing and signed by both parties.',
        help_text="Entire agreement clause text"
    )
    
    # Audit Trail
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contracts_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contracts'
        ordering = ['-start_date']
        
    def __str__(self):
        return f"{self.contract_number} - {self.client_organization}"
    
    @property
    def client_name(self):
        """Get client name for compatibility with frontend"""
        return self.client_organization
    
    @property
    def total_standards_count(self):
        """Calculate total number of ISO standards in this contract"""
        return len(self.iso_standards) if self.iso_standards else 0
    
    @property
    def total_year_1_fee(self):
        """Calculate total Year 1 fee (certification audit)"""
        return self.fee_per_standard_year_1 * self.total_standards_count
    
    @property
    def total_year_2_fee(self):
        """Calculate total Year 2 fee (surveillance audit)"""
        return self.fee_per_standard_year_2 * self.total_standards_count
    
    @property
    def total_year_3_fee(self):
        """Calculate total Year 3 fee (surveillance audit)"""
        return self.fee_per_standard_year_3 * self.total_standards_count
    
    @property
    def client_from_opportunity(self):
        """Get client from the linked opportunity"""
        return self.opportunity.client if self.opportunity else None
    
    def generate_from_template(self, template: ContractTemplate, contract_data: dict):
        """
        Generate contract content from template and populate database fields
        """
        self.contract_template = template
        self.template_version_used = template.version
        
        # Extract data from template and populate contract fields
        template_metadata = template.template_data.get('metadata', {})
        contract_form_data = template_metadata.get('contractData', {})
        
        if contract_form_data:
            # Map template form data to contract model fields
            self.client_organization = contract_form_data.get('clientName', '')
            self.client_address = contract_form_data.get('clientAddress', '')
            self.client_contact_person = contract_form_data.get('clientContact', '')
            self.client_email = contract_form_data.get('clientEmail', '')
            self.cb_name = contract_form_data.get('companyName', 'AceQu International Limited')
            self.cb_address = contract_form_data.get('companyAddress', '168 City Road, Cardiff, Wales, CF24 3JE, United Kingdom')
            self.scope_of_work = contract_form_data.get('serviceScope', '')
            
            # Map fee structure
            self.fee_per_standard_year_1 = contract_form_data.get('initialCertificationCost', 1000)
            self.fee_per_standard_year_2 = contract_form_data.get('firstSurveillanceCost', 1000)
            self.fee_per_standard_year_3 = contract_form_data.get('secondSurveillanceCost', 1000)
            self.recertification_fee = contract_form_data.get('recertificationCost', None)
            
            # Calculate contract value
            total_value = (
                self.fee_per_standard_year_1 + 
                self.fee_per_standard_year_2 + 
                self.fee_per_standard_year_3
            )
            if self.recertification_fee:
                total_value += self.recertification_fee
            self.contract_value = total_value
            
            # Set contract dates
            import datetime
            if contract_form_data.get('contractDate'):
                self.agreement_date = datetime.datetime.fromisoformat(contract_form_data['contractDate'].replace('Z', '+00:00')).date()
            if contract_form_data.get('startDate'):
                self.start_date = datetime.datetime.fromisoformat(contract_form_data['startDate'].replace('Z', '+00:00')).date()
            if contract_form_data.get('endDate'):
                self.end_date = datetime.datetime.fromisoformat(contract_form_data['endDate'].replace('Z', '+00:00')).date()


class ActivityLog(models.Model):
    ACTIVITY_TYPES = [
        ('CALL', 'Phone Call'),
        ('EMAIL', 'Email'),
        ('MEETING', 'Meeting'),
        ('PROPOSAL', 'Proposal'),
        ('FOLLOW_UP', 'Follow-up'),
        ('NOTE', 'Note'),
    ]

    # Relationships (one of these will be filled)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='bd_activities')
    
    # Activity Details
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    
    # Timeline
    activity_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Assignment
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bd_activity_logs'
        ordering = ['-activity_date']
        
    def __str__(self):
        return f"{self.activity_type} - {self.subject}"