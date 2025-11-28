from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('IN_REVIEW', 'In Review'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('ON_HOLD', 'On Hold'),
    ]

    TASK_TYPES = [
        ('AUDIT', 'Audit Task'),
        ('CONSULTING', 'Consulting Task'),
        ('BUSINESS_DEV', 'Business Development'),
        ('ADMIN', 'Administrative'),
        ('TRAINING', 'Training'),
        ('FOLLOW_UP', 'Follow-up'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default='ADMIN')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')

    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks_assigned')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tasks_created')

    # Relationships
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks')

    # Timeline
    due_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.PositiveIntegerField(null=True, blank=True)
    actual_hours = models.PositiveIntegerField(null=True, blank=True)

    # Metadata
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags
    progress_percentage = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task_comments'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on {self.task.title} by {self.author.username}"


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'task_attachments'

    def __str__(self):
        return f"{self.file_name} - {self.task.title}"


class TaskTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    task_type = models.CharField(max_length=20, choices=Task.TASK_TYPES)
    template_data = models.JSONField()  # Store template structure

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task_templates'

    def __str__(self):
        return self.name


class TaskRecurrence(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    task_template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    interval = models.PositiveIntegerField(default=1)  # Every X days/weeks/months
    next_run_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task_recurrences'

    def __str__(self):
        return f"{self.task_template.name} - {self.frequency}"



class Workflow(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('ON_HOLD', 'On Hold'),
    ]

    WORKFLOW_TYPES = [
        ('AUDIT_PROCESS', 'Audit Process'),
        ('CERTIFICATION', 'Certification'),
        ('CLIENT_ONBOARDING', 'Client Onboarding'),
        ('COMPLIANCE_CHECK', 'Compliance Check'),
        ('REVIEW_PROCESS', 'Review Process'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    workflow_type = models.CharField(max_length=30, choices=WORKFLOW_TYPES, default='AUDIT_PROCESS')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')

    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='workflows_assigned')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='workflows_created')

    # Relationships
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='workflows')
    template = models.ForeignKey('WorkflowTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='workflow_instances')

    # Timeline
    due_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    estimated_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Estimated duration in minutes")

    # Progress
    current_step = models.PositiveIntegerField(default=0)
    completion_rate = models.PositiveIntegerField(default=0, help_text="Completion percentage")

    # Approval
    approval_required = models.BooleanField(default=False)
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='workflows_to_approve')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflows'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"


class WorkflowStep(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('SKIPPED', 'Skipped'),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='workflow_steps_assigned')

    # Timeline
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Dependencies
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependent_steps')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_steps'
        ordering = ['workflow', 'order']

    def __str__(self):
        return f"{self.workflow.title} - Step {self.order}: {self.title}"


class WorkflowTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    workflow_type = models.CharField(max_length=30, choices=Workflow.WORKFLOW_TYPES)
    template_data = models.JSONField(help_text="Store template structure including steps")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_templates'

    def __str__(self):
        return self.name
