from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.business_development.models import Lead, Opportunity, Contract
from apps.audits.models import Audit


class JobPipeline(models.Model):
    """
    Tracks the progression of jobs through the business process:
    Lead -> Opportunity -> Contract -> Audit
    """
    
    STAGE_CHOICES = [
        ('LEAD', 'Lead'),
        ('OPPORTUNITY', 'Opportunity'),
        ('CONTRACT', 'Contract'),
        ('AUDIT_SCHEDULED', 'Audit Scheduled'),
        ('AUDIT_IN_PROGRESS', 'Audit In Progress'),
        ('AUDIT_COMPLETED', 'Audit Completed'),
        ('CERTIFICATE_ISSUED', 'Certificate Issued'),
        ('SURVEILLANCE_DUE', 'Surveillance Due'),
        ('CLOSED', 'Closed'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ON_HOLD', 'On Hold'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    # Core Information
    number = models.PositiveIntegerField(unique=True, null=True, blank=True, help_text="Sequential pipeline number")
    pipeline_id = models.CharField(max_length=50, unique=True, blank=True, help_text="Unique pipeline identifier")
    client_name = models.CharField(max_length=255, help_text="Client organization name")
    service_description = models.TextField(help_text="Description of services")
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    def save(self, *args, **kwargs):
        if not self.number:
            last_pipeline = JobPipeline.objects.order_by('-number').first()
            self.number = (last_pipeline.number + 1) if last_pipeline and last_pipeline.number else 1
            
        if not self.pipeline_id:
            self.pipeline_id = f"PL-{self.number:05d}"
            
        super().save(*args, **kwargs)
    
    # Current Stage
    current_stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='LEAD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Related Objects (polymorphic relationships)
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='pipelines')
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name='pipelines')
    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True, related_name='pipelines')
    
    # Audits (can have multiple audits per pipeline)
    # Related through foreign key in Audit model
    
    # Timeline tracking
    lead_created_date = models.DateTimeField(null=True, blank=True)
    opportunity_created_date = models.DateTimeField(null=True, blank=True)
    contract_signed_date = models.DateTimeField(null=True, blank=True)
    audit_scheduled_date = models.DateTimeField(null=True, blank=True)
    audit_completed_date = models.DateTimeField(null=True, blank=True)
    certificate_issued_date = models.DateTimeField(null=True, blank=True)
    
    # Next milestones
    next_milestone = models.CharField(max_length=255, blank=True)
    next_milestone_date = models.DateField(null=True, blank=True)
    
    # Assignment
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_pipelines')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_pipelines')
    
    class Meta:
        db_table = 'job_pipelines'
        ordering = ['-updated_at']
        
    def __str__(self):
        return f"{self.pipeline_id} - {self.client_name} ({self.current_stage})"
    
    @property
    def stage_progress_percentage(self):
        """Calculate progress based on current stage"""
        stage_weights = {
            'LEAD': 10,
            'OPPORTUNITY': 25,
            'CONTRACT': 50,
            'AUDIT_SCHEDULED': 70,
            'AUDIT_IN_PROGRESS': 85,
            'AUDIT_COMPLETED': 95,
            'CERTIFICATE_ISSUED': 100,
            'SURVEILLANCE_DUE': 100,
            'CLOSED': 100,
        }
        return stage_weights.get(self.current_stage, 0)
    
    @property
    def days_in_current_stage(self):
        """Calculate days spent in current stage"""
        from django.utils import timezone
        stage_start_dates = {
            'LEAD': self.lead_created_date,
            'OPPORTUNITY': self.opportunity_created_date,
            'CONTRACT': self.contract_signed_date,
            'AUDIT_SCHEDULED': self.audit_scheduled_date,
            'AUDIT_IN_PROGRESS': self.audit_scheduled_date,
            'AUDIT_COMPLETED': self.audit_completed_date,
            'CERTIFICATE_ISSUED': self.certificate_issued_date,
        }
        
        start_date = stage_start_dates.get(self.current_stage)
        if start_date:
            return (timezone.now() - start_date).days
        return 0
    
    @property
    def current_audits(self):
        """Get current audits for this pipeline"""
        return self.audits.filter(status__in=['PLANNED', 'IN_PROGRESS'])
    
    @property
    def completed_audits(self):
        """Get completed audits for this pipeline"""
        return self.audits.filter(status='COMPLETED')

    @property
    def opportunity_ref(self):
        """Formatted reference for opportunity"""
        return f"PL-O-{self.number:05d}" if self.opportunity and self.number else None

    @property
    def contract_ref(self):
        """Formatted reference for contract"""
        return f"PL-C-{self.number:05d}" if self.contract and self.number else None
    
    def get_audit_ref(self, audit):
        """Formatted reference for a specific audit"""
        # We might want to number audits sequentially within the pipeline if there are multiple
        # For now, let's just use PL-A-{number} and maybe append index if needed
        # But user example was PL-A-0001. If multiple audits, maybe PL-A-0001-1?
        # Let's assume 1-to-1 mapping for the main audit flow for now, or just use the pipeline number
        return f"PL-A-{self.number:05d}" if self.number else None
    
    def advance_stage(self, new_stage, user=None):
        """Advance pipeline to next stage with validation"""
        from django.utils import timezone
        
        # Validate stage progression
        valid_progressions = {
            'LEAD': ['OPPORTUNITY', 'CLOSED'],
            'OPPORTUNITY': ['CONTRACT', 'CLOSED'],
            'CONTRACT': ['AUDIT_SCHEDULED', 'CLOSED'],
            'AUDIT_SCHEDULED': ['AUDIT_IN_PROGRESS'],
            'AUDIT_IN_PROGRESS': ['AUDIT_COMPLETED'],
            'AUDIT_COMPLETED': ['CERTIFICATE_ISSUED', 'SURVEILLANCE_DUE'],
            'CERTIFICATE_ISSUED': ['SURVEILLANCE_DUE', 'CLOSED'],
            'SURVEILLANCE_DUE': ['AUDIT_SCHEDULED', 'CLOSED'],
        }
        
        if new_stage not in valid_progressions.get(self.current_stage, []):
            raise ValueError(f"Cannot advance from {self.current_stage} to {new_stage}")
        
        # Update stage
        old_stage = self.current_stage
        self.current_stage = new_stage
        
        # Update relevant timestamps
        now = timezone.now()
        if new_stage == 'OPPORTUNITY':
            self.opportunity_created_date = now
        elif new_stage == 'CONTRACT':
            self.contract_signed_date = now
        elif new_stage == 'AUDIT_SCHEDULED':
            self.audit_scheduled_date = now
        elif new_stage == 'AUDIT_COMPLETED':
            self.audit_completed_date = now
        elif new_stage == 'CERTIFICATE_ISSUED':
            self.certificate_issued_date = now
        
        self.save()
        
        # Create stage transition log
        PipelineStageTransition.objects.create(
            pipeline=self,
            from_stage=old_stage,
            to_stage=new_stage,
            transitioned_by=user,
            transitioned_at=now
        )
    
    def update_from_related_object(self, obj, user=None):
        """Update pipeline when related object changes"""
        from django.utils import timezone
        
        if isinstance(obj, Lead):
            self.lead = obj
            if self.current_stage == 'LEAD':
                self.client_name = obj.company_name
                self.estimated_value = obj.estimated_value
                self.currency = obj.currency
                
        elif isinstance(obj, Opportunity):
            self.opportunity = obj
            if obj.status == 'CLOSED_WON' and self.current_stage in ['LEAD', 'OPPORTUNITY']:
                self.advance_stage('OPPORTUNITY' if self.current_stage == 'LEAD' else 'CONTRACT', user)
            self.client_name = obj.client.name if obj.client else self.client_name
            self.estimated_value = obj.estimated_value
            self.currency = obj.currency
            
        elif isinstance(obj, Contract):
            self.contract = obj
            if obj.status == 'ACTIVE' and self.current_stage in ['LEAD', 'OPPORTUNITY', 'CONTRACT']:
                self.advance_stage('CONTRACT', user)
            self.client_name = obj.client_organization
            self.estimated_value = obj.contract_value
            self.currency = obj.currency
            
        elif isinstance(obj, Audit):
            if obj.status == 'PLANNED' and self.current_stage == 'CONTRACT':
                self.advance_stage('AUDIT_SCHEDULED', user)
            elif obj.status == 'IN_PROGRESS' and self.current_stage == 'AUDIT_SCHEDULED':
                self.advance_stage('AUDIT_IN_PROGRESS', user)
            elif obj.status == 'COMPLETED' and self.current_stage == 'AUDIT_IN_PROGRESS':
                self.advance_stage('AUDIT_COMPLETED', user)
        
        self.save()


class PipelineStageTransition(models.Model):
    """Track stage transitions for audit and analytics"""
    
    pipeline = models.ForeignKey(JobPipeline, on_delete=models.CASCADE, related_name='stage_transitions')
    from_stage = models.CharField(max_length=20, choices=JobPipeline.STAGE_CHOICES)
    to_stage = models.CharField(max_length=20, choices=JobPipeline.STAGE_CHOICES)
    transitioned_at = models.DateTimeField(auto_now_add=True)
    transitioned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pipeline_stage_transitions'
        ordering = ['-transitioned_at']
        
    def __str__(self):
        return f"{self.pipeline.pipeline_id}: {self.from_stage} → {self.to_stage}"


class PipelineMilestone(models.Model):
    """Track important milestones and deadlines in the pipeline"""
    
    MILESTONE_TYPES = [
        ('PROPOSAL_DUE', 'Proposal Due'),
        ('CONTRACT_SIGNATURE', 'Contract Signature'),
        ('AUDIT_SCHEDULED', 'Audit Scheduled'),
        ('AUDIT_START', 'Audit Start'),
        ('AUDIT_COMPLETION', 'Audit Completion'),
        ('CERTIFICATE_ISSUE', 'Certificate Issue'),
        ('SURVEILLANCE_DUE', 'Surveillance Due'),
        ('RECERTIFICATION_DUE', 'Recertification Due'),
        ('CONTRACT_RENEWAL', 'Contract Renewal'),
        ('CUSTOM', 'Custom Milestone'),
    ]
    
    pipeline = models.ForeignKey(JobPipeline, on_delete=models.CASCADE, related_name='milestones')
    milestone_type = models.CharField(max_length=20, choices=MILESTONE_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    is_critical = models.BooleanField(default=False)
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pipeline_milestones'
        ordering = ['due_date']
        
    def __str__(self):
        return f"{self.pipeline.pipeline_id}: {self.title}"
    
    @property
    def is_overdue(self):
        """Check if milestone is overdue"""
        from django.utils import timezone
        return not self.is_completed and self.due_date < timezone.now().date()
    
    @property
    def days_remaining(self):
        """Calculate days remaining until due date"""
        from django.utils import timezone
        today = timezone.now().date()
        return (self.due_date - today).days if self.due_date >= today else 0

