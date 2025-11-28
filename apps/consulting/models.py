from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client


class ConsultingProject(models.Model):
    STATUS_CHOICES = [
        ('PLANNING', 'Planning'),
        ('IN_PROGRESS', 'In Progress'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PROJECT_TYPES = [
        ('STRATEGY', 'Strategy Consulting'),
        ('PROCESS', 'Process Improvement'),
        ('DIGITAL', 'Digital Transformation'),
        ('CHANGE', 'Change Management'),
        ('RISK', 'Risk Management'),
        ('COMPLIANCE', 'Compliance'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='consulting_projects')
    project_name = models.CharField(max_length=255)
    project_code = models.CharField(max_length=50, unique=True)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES)
    description = models.TextField()
    
    # Timeline
    start_date = models.DateField()
    end_date = models.DateField()
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Financial
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    billing_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNING')
    progress_percentage = models.PositiveIntegerField(default=0)
    
    # Team
    project_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_projects')
    team_members = models.ManyToManyField(User, related_name='consulting_projects', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='consulting_projects_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'consulting_projects'
        ordering = ['-start_date']
        
    def __str__(self):
        return f"{self.project_code} - {self.project_name}"


class ProjectPhase(models.Model):
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ON_HOLD', 'On Hold'),
    ]

    project = models.ForeignKey(ConsultingProject, on_delete=models.CASCADE, related_name='phases')
    phase_name = models.CharField(max_length=255)
    description = models.TextField()
    order = models.PositiveIntegerField()
    
    # Timeline
    planned_start_date = models.DateField()
    planned_end_date = models.DateField()
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')
    progress_percentage = models.PositiveIntegerField(default=0)
    
    # Resources
    estimated_hours = models.PositiveIntegerField()
    actual_hours = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'project_phases'
        ordering = ['order']
        
    def __str__(self):
        return f"{self.project.project_code} - Phase {self.order}: {self.phase_name}"


class Deliverable(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('DELIVERED', 'Delivered'),
    ]

    project = models.ForeignKey(ConsultingProject, on_delete=models.CASCADE, related_name='deliverables')
    phase = models.ForeignKey(ProjectPhase, on_delete=models.SET_NULL, null=True, blank=True)
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    deliverable_type = models.CharField(max_length=50)  # Report, Presentation, Software, etc.
    
    # Timeline
    due_date = models.DateField()
    delivered_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Assignment
    responsible_consultant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Files
    file = models.FileField(upload_to='deliverables/', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'deliverables'
        ordering = ['due_date']
        
    def __str__(self):
        return f"{self.title} - {self.project.project_code}"


class ConsultantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='consultant_profile')
    title = models.CharField(max_length=100)
    skills = models.TextField(help_text="Comma-separated list of skills")
    target_utilization = models.PositiveIntegerField(default=80)
    current_utilization = models.PositiveIntegerField(default=0)
    billable_hours_ytd = models.PositiveIntegerField(default=0)
    revenue_ytd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    availability_status = models.CharField(max_length=100, default="Available")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"


class ClientHealth(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='health_metrics')
    health_score = models.PositiveIntegerField(default=100)
    satisfaction_score = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    engagement_level = models.CharField(max_length=20, choices=[('HIGH', 'High'), ('MEDIUM', 'Medium'), ('LOW', 'Low')], default='HIGH')
    last_contact_date = models.DateField(auto_now=True)
    risk_factors = models.TextField(blank=True, help_text="JSON list of risk factors")
    account_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_accounts')
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client.name} - Health: {self.health_score}"


class ProjectRisk(models.Model):
    RISK_LEVELS = [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')]
    STATUS_CHOICES = [('OPEN', 'Open'), ('MITIGATED', 'Mitigated'), ('CLOSED', 'Closed')]

    project = models.ForeignKey(ConsultingProject, on_delete=models.CASCADE, related_name='risks')
    title = models.CharField(max_length=255)
    description = models.TextField()
    impact = models.CharField(max_length=10, choices=RISK_LEVELS)
    probability = models.CharField(max_length=10, choices=RISK_LEVELS)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    mitigation_plan = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project.project_code} - {self.title}"


class ClientFeedback(models.Model):
    project = models.ForeignKey(ConsultingProject, on_delete=models.CASCADE, related_name='feedback')
    client_contact = models.CharField(max_length=100)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.client.name} - {self.rating}/5"


class ProjectMilestone(models.Model):
    project = models.ForeignKey(ConsultingProject, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'), 
        ('ON_TRACK', 'On Track'), 
        ('AT_RISK', 'At Risk'), 
        ('DELAYED', 'Delayed'), 
        ('COMPLETED', 'Completed')
    ], default='PENDING')
    
    def __str__(self):
        return f"{self.project.project_code} - {self.title}"