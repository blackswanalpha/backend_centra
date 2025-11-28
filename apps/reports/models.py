from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client


class ReportTemplate(models.Model):
    REPORT_TYPES = [
        ('FINANCIAL', 'Financial Report'),
        ('AUDIT', 'Audit Report'),
        ('CLIENT', 'Client Report'),
        ('PERFORMANCE', 'Performance Report'),
        ('COMPLIANCE', 'Compliance Report'),
        ('CUSTOM', 'Custom Report'),
    ]

    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Template Configuration
    template_config = models.JSONField()  # Store report structure and parameters
    is_public = models.BooleanField(default=False)
    
    # System Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='report_templates_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_templates'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class GeneratedReport(models.Model):
    STATUS_CHOICES = [
        ('GENERATING', 'Generating'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('SCHEDULED', 'Scheduled'),
    ]

    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='generated_reports')
    
    # Report Details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Parameters
    parameters = models.JSONField()  # Store report parameters used
    
    # Date Range
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Filters
    client_filter = models.ManyToManyField(Client, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='GENERATING')
    
    # Files
    report_file = models.FileField(upload_to='reports/', blank=True)
    file_format = models.CharField(max_length=10, default='PDF')  # PDF, Excel, CSV
    
    # Generation Info
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_generated')
    generation_time = models.DurationField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Scheduling
    is_scheduled = models.BooleanField(default=False)
    schedule_frequency = models.CharField(max_length=20, blank=True)  # daily, weekly, monthly
    next_run_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'generated_reports'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d')}"


class ReportShare(models.Model):
    PERMISSION_TYPES = [
        ('VIEW', 'View Only'),
        ('DOWNLOAD', 'Download'),
    ]

    report = models.ForeignKey(GeneratedReport, on_delete=models.CASCADE, related_name='shares')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.CharField(max_length=10, choices=PERMISSION_TYPES, default='VIEW')
    
    # Access Control
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Tracking
    last_accessed = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)
    
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='report_shares_created')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'report_shares'
        unique_together = ['report', 'shared_with']
        
    def __str__(self):
        return f"{self.report.title} shared with {self.shared_with.username}"


class Dashboard(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Configuration
    layout_config = models.JSONField()  # Store dashboard layout and widgets
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    # Assignment
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboards')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dashboards'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class DashboardWidget(models.Model):
    WIDGET_TYPES = [
        ('CHART', 'Chart'),
        ('TABLE', 'Table'),
        ('METRIC', 'Metric'),
        ('LIST', 'List'),
        ('CALENDAR', 'Calendar'),
    ]

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets')
    
    # Widget Details
    title = models.CharField(max_length=255)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    
    # Configuration
    config = models.JSONField()  # Store widget-specific configuration
    data_source = models.CharField(max_length=100)  # API endpoint or data source
    
    # Layout
    position_x = models.PositiveIntegerField(default=0)
    position_y = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=1)
    height = models.PositiveIntegerField(default=1)
    
    # Refresh
    refresh_interval = models.PositiveIntegerField(default=300)  # seconds
    last_updated = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dashboard_widgets'
        ordering = ['position_y', 'position_x']
        
    def __str__(self):
        return f"{self.title} - {self.dashboard.name}"