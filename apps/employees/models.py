from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'departments'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Position(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    description = models.TextField(blank=True)
    level = models.PositiveIntegerField(default=1)  # 1-10 hierarchy level
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'positions'
        ordering = ['department', 'level', 'title']
        
    def __str__(self):
        return f"{self.title} - {self.department.name}"


class Employee(models.Model):
    EMPLOYMENT_STATUS = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('TERMINATED', 'Terminated'),
        ('RESIGNED', 'Resigned'),
        ('ON_LEAVE', 'On Leave'),
    ]
    
    EMPLOYMENT_TYPE = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERN', 'Intern'),
        ('CONSULTANT', 'Consultant'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    national_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    passport_number = models.CharField(max_length=20, blank=True)

    # Contact Information
    personal_email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    # Address
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Employment Details
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE, default='FULL_TIME')
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, default='ACTIVE')
    hire_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)

    # Compensation
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='KES')
    
    # Work Schedule
    work_hours_per_week = models.PositiveIntegerField(default=40)

    # Professional Details
    role = models.CharField(max_length=50, blank=True, help_text="Job role/title (e.g., lead-auditor, auditor, etc.)")
    department_name = models.CharField(max_length=100, blank=True, help_text="Department name for display")
    certifications = models.JSONField(default=list, blank=True, help_text="List of certifications")
    experience_years = models.PositiveIntegerField(default=0, help_text="Years of experience")
    languages = models.JSONField(default=list, blank=True, help_text="Languages spoken")

    # Performance Metrics
    utilization = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Utilization percentage")
    satisfaction = models.DecimalField(max_digits=3, decimal_places=1, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)], help_text="Satisfaction rating 0-5")

    # Commission Settings (for auditors)
    commission_enabled = models.BooleanField(default=False)
    commission_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Commission rate per audit")
    audit_count = models.PositiveIntegerField(default=0, help_text="Total audits completed")

    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employees'
        ordering = ['first_name', 'last_name']
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class EmployeeSkill(models.Model):
    PROFICIENCY_LEVELS = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('EXPERT', 'Expert'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=100)
    proficiency_level = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS)
    years_of_experience = models.PositiveIntegerField(default=0)
    certified = models.BooleanField(default=False)
    certification_date = models.DateField(null=True, blank=True)
    certification_expiry = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employee_skills'
        unique_together = ['employee', 'skill_name']
        
    def __str__(self):
        return f"{self.employee.full_name} - {self.skill_name} ({self.proficiency_level})"


class PerformanceReview(models.Model):
    REVIEW_TYPES = [
        ('QUARTERLY', 'Quarterly Review'),
        ('ANNUAL', 'Annual Review'),
        ('PROBATION', 'Probation Review'),
        ('PROJECT', 'Project Review'),
    ]
    
    RATING_CHOICES = [
        (1, 'Needs Improvement'),
        (2, 'Below Expectations'),
        (3, 'Meets Expectations'),
        (4, 'Exceeds Expectations'),
        (5, 'Outstanding'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reviews_given')
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPES)
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    
    # Ratings
    overall_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    technical_skills_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    teamwork_rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    leadership_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Comments
    achievements = models.TextField()
    areas_for_improvement = models.TextField()
    goals_next_period = models.TextField()
    reviewer_comments = models.TextField()
    employee_comments = models.TextField(blank=True)
    
    # Status
    is_finalized = models.BooleanField(default=False)
    employee_acknowledged = models.BooleanField(default=False)
    acknowledgment_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'performance_reviews'
        ordering = ['-review_period_end']
        
    def __str__(self):
        return f"{self.employee.full_name} - {self.review_type} ({self.review_period_end})"


class TimeSheet(models.Model):
    TASK_TYPE_CHOICES = [
        ('1ST_SURVEILLANCE', '1st Surveillance Audit'),
        ('2ND_SURVEILLANCE', '2nd Surveillance Audit'),
        ('RE_CERTIFICATION', 'Re-certification Audit'),
        ('INITIAL_CERTIFICATION', 'Initial Certification Audit'),
        ('GAP_ANALYSIS', 'Gap Analysis'),
        ('CONSULTING', 'Consulting'),
        ('TRAINING', 'Training'),
        ('ADMIN', 'Administrative'),
    ]
    
    BILLABLE_STATUS_CHOICES = [
        ('BILLABLE', 'Billable'),
        ('NON_BILLABLE', 'Non-Billable'),
        ('INTERNAL', 'Internal'),
    ]
    
    BILLED_STATUS_CHOICES = [
        ('UNBILLED', 'Unbilled'),
        ('BILLED', 'Billed'),
        ('INVOICED', 'Invoiced'),
        ('PAID', 'Paid'),
    ]
    
    # Core Information (from Excel structure)
    certificate_no = models.CharField(max_length=100, blank=True, help_text="Certificate or project number")
    task_name = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, default='ADMIN')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='timesheets')
    date = models.DateField()
    notes = models.TextField(blank=True, help_text="Location or additional notes")
    
    # Billing Information (from Excel)
    billable_status = models.CharField(max_length=20, choices=BILLABLE_STATUS_CHOICES, default='BILLABLE')
    billed_status = models.CharField(max_length=20, choices=BILLED_STATUS_CHOICES, default='UNBILLED')
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Billable amount")
    currency = models.CharField(max_length=3, default='KES')
    
    # Time Tracking (existing functionality)
    regular_hours = models.DecimalField(max_digits=5, decimal_places=2, default=8.0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Time stamps
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    
    # Work description
    work_description = models.TextField(blank=True)
    project_code = models.CharField(max_length=50, blank=True, help_text="Project or client code")
    
    # Client Association
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='timesheets')
    
    # Approval Workflow
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='timesheets_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Audit Trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='timesheets_created')
    
    class Meta:
        db_table = 'timesheets'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['billable_status']),
            models.Index(fields=['billed_status']),
            models.Index(fields=['certificate_no']),
            models.Index(fields=['client']),
        ]
        
    def __str__(self):
        return f"{self.employee.full_name} - {self.get_task_name_display()} - {self.date}"
    
    @property
    def total_hours(self):
        """Calculate total hours worked"""
        return self.regular_hours + self.overtime_hours
    
    @property
    def billable_hours(self):
        """Calculate billable hours based on status"""
        if self.billable_status == 'BILLABLE':
            return self.total_hours
        return 0
    
    def calculate_amount(self, hourly_rate=None):
        """Calculate billable amount based on hours and rate"""
        if not hourly_rate:
            # Try to get rate from employee profile
            hourly_rate = getattr(self.employee, 'hourly_rate', 75.0)  # Default rate
        
        regular_amount = float(self.regular_hours) * hourly_rate
        overtime_amount = float(self.overtime_hours) * hourly_rate * 1.5  # Overtime multiplier
        
        return regular_amount + overtime_amount