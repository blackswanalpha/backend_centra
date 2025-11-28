from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Department, Position, EmployeeSkill, PerformanceReview, TimeSheet


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PositionSerializer(serializers.ModelSerializer):
    """Serializer for Position model"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Position
        fields = ['id', 'title', 'department', 'department_name', 'description', 'level', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSkillSerializer(serializers.ModelSerializer):
    """Serializer for EmployeeSkill model"""
    
    class Meta:
        model = EmployeeSkill
        fields = ['id', 'skill_name', 'proficiency_level', 'years_of_experience', 'certified', 
                  'certification_date', 'certification_expiry', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer for Employee model
    Maps Django model fields to frontend camelCase format
    """
    # Read-only computed fields
    fullName = serializers.CharField(source='full_name', read_only=True)
    
    # Map frontend field names to backend (camelCase to snake_case)
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')
    middleName = serializers.CharField(source='middle_name', required=False, allow_blank=True)
    dateOfBirth = serializers.DateField(source='date_of_birth', required=False, allow_null=True)
    nationalId = serializers.CharField(source='national_id', required=False, allow_blank=True)
    passportNumber = serializers.CharField(source='passport_number', required=False, allow_blank=True)

    # Contact fields
    email = serializers.EmailField(source='personal_email', required=False, allow_blank=True)
    phone = serializers.CharField(source='phone_number', required=False, allow_blank=True)
    emergencyContact = serializers.CharField(source='emergency_contact_name', required=False, allow_blank=True)
    emergencyPhone = serializers.CharField(source='emergency_contact_phone', required=False, allow_blank=True)

    # Address fields
    address = serializers.CharField(source='address_line_1', required=False, allow_blank=True)
    addressLine2 = serializers.CharField(source='address_line_2', required=False, allow_blank=True)
    county = serializers.CharField(required=False, allow_blank=True)
    zipCode = serializers.CharField(source='postal_code', required=False, allow_blank=True)

    # Employment fields
    employeeId = serializers.CharField(source='employee_id', read_only=True)
    status = serializers.CharField(source='employment_status', required=False)
    employmentType = serializers.CharField(source='employment_type', required=False)
    hireDate = serializers.DateField(source='hire_date', required=False, allow_null=True)
    terminationDate = serializers.DateField(source='termination_date', required=False, allow_null=True)

    # Department and position
    department = serializers.CharField(source='department_name', required=False, allow_blank=True)
    positionId = serializers.IntegerField(source='position.id', required=False, allow_null=True)
    positionTitle = serializers.CharField(source='position.title', read_only=True)

    # Professional details
    experience = serializers.IntegerField(source='experience_years', required=False)

    # Compensation
    baseSalary = serializers.DecimalField(source='base_salary', max_digits=10, decimal_places=2, required=False, allow_null=True)

    # Commission
    commissionEnabled = serializers.BooleanField(source='commission_enabled', required=False)
    commissionRate = serializers.DecimalField(source='commission_rate', max_digits=10, decimal_places=2, required=False)
    auditCount = serializers.IntegerField(source='audit_count', required=False)
    
    # Timestamps
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    
    # Related data
    skills = EmployeeSkillSerializer(many=True, read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employeeId', 'firstName', 'lastName', 'middleName', 'fullName',
            'dateOfBirth', 'gender', 'nationalId', 'passportNumber',
            'email', 'phone', 'emergencyContact', 'emergencyPhone',
            'address', 'addressLine2', 'city', 'county', 'zipCode',
            'role', 'department', 'positionId', 'positionTitle',
            'employmentType', 'status', 'hireDate', 'terminationDate',
            'baseSalary', 'currency', 'work_hours_per_week',
            'certifications', 'experience', 'languages',
            'utilization', 'satisfaction',
            'commissionEnabled', 'commissionRate', 'auditCount',
            'createdAt', 'updatedAt', 'skills'
        ]
        read_only_fields = ['id', 'employeeId', 'fullName', 'positionTitle', 'createdAt', 'updatedAt']
    
    def validate_status(self, value):
        """Validate and normalize status values"""
        # Map frontend status values to backend
        status_map = {
            'active': 'ACTIVE',
            'inactive': 'INACTIVE',
            'on-leave': 'ON_LEAVE',
            'terminated': 'TERMINATED',
            'resigned': 'RESIGNED'
        }
        
        # If value is already uppercase, use it directly
        if value.upper() in dict(Employee.EMPLOYMENT_STATUS).keys():
            return value.upper()
        
        # Otherwise, try to map from frontend format
        normalized = status_map.get(value.lower())
        if not normalized:
            raise serializers.ValidationError(f"Invalid status: {value}")
        
        return normalized
    
    def to_representation(self, instance):
        """Convert backend data to frontend format"""
        data = super().to_representation(instance)
        
        # Map backend status to frontend format
        status_map = {
            'ACTIVE': 'active',
            'INACTIVE': 'inactive',
            'ON_LEAVE': 'on-leave',
            'TERMINATED': 'terminated',
            'RESIGNED': 'resigned'
        }
        
        if data.get('status'):
            data['status'] = status_map.get(data['status'], data['status'].lower())
        
        return data


class TimeSheetSerializer(serializers.ModelSerializer):
    """Serializer for TimeSheet model with Excel data structure support"""
    
    # Employee information
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_email = serializers.CharField(source='employee.personal_email', read_only=True)
    employee_data = EmployeeSerializer(source='employee', read_only=True)
    
    # Client information
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_data = serializers.SerializerMethodField()
    
    # Calculated fields
    total_hours = serializers.ReadOnlyField()
    billable_hours = serializers.ReadOnlyField()
    calculated_amount = serializers.SerializerMethodField()
    
    # Display choices
    task_name_display = serializers.CharField(source='get_task_name_display', read_only=True)
    billable_status_display = serializers.CharField(source='get_billable_status_display', read_only=True)
    billed_status_display = serializers.CharField(source='get_billed_status_display', read_only=True)
    
    # Approval information
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = TimeSheet
        fields = [
            'id', 'certificate_no', 'task_name', 'task_name_display', 'employee', 
            'employee_name', 'employee_email', 'employee_data', 'date', 'notes',
            'billable_status', 'billable_status_display', 'billed_status', 'billed_status_display',
            'amount', 'currency', 'regular_hours', 'overtime_hours', 'break_hours',
            'total_hours', 'billable_hours', 'calculated_amount',
            'clock_in', 'clock_out', 'work_description', 'project_code',
            'client', 'client_name', 'client_data',
            'approved', 'approved_by', 'approved_by_name', 'approved_at',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'approved_at', 'total_hours', 'billable_hours']
    
    def get_client_data(self, obj):
        if obj.client:
            return {
                'id': obj.client.id,
                'company_name': obj.client.name,
                'email': obj.client.email,
                'currency_code': getattr(obj.client, 'currency_code', 'KES')
            }
        return None
    
    def get_calculated_amount(self, obj):
        """Return calculated amount based on hours and rate"""
        return obj.calculate_amount()
    
    def create(self, validated_data):
        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # If approval status changes, set approval timestamp and user
        if 'approved' in validated_data and validated_data['approved'] != instance.approved:
            if validated_data['approved']:
                validated_data['approved_by'] = self.context['request'].user
                from django.utils import timezone
                validated_data['approved_at'] = timezone.now()
            else:
                validated_data['approved_by'] = None
                validated_data['approved_at'] = None
        
        return super().update(instance, validated_data)


class TimeSheetSummarySerializer(serializers.Serializer):
    """Serializer for timesheet statistics and summaries"""
    total_entries = serializers.IntegerField()
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    billable_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Breakdown by status
    by_billable_status = serializers.DictField()
    by_billed_status = serializers.DictField()
    by_task_type = serializers.DictField()
    
    # Date range
    date_from = serializers.DateField()
    date_to = serializers.DateField()


class PerformanceReviewSerializer(serializers.ModelSerializer):
    """Serializer for PerformanceReview model"""
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    
    class Meta:
        model = PerformanceReview
        fields = [
            'id', 'employee', 'employee_name', 'reviewer', 'reviewer_name',
            'review_period_start', 'review_period_end', 'review_type', 'status',
            'overall_rating', 'goals_achievement_rating', 'skills_rating',
            'communication_rating', 'teamwork_rating', 'leadership_rating',
            'achievements', 'areas_for_improvement', 'goals_next_period',
            'reviewer_comments', 'employee_comments', 'is_finalized',
            'employee_acknowledged', 'acknowledgment_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'acknowledgment_date']

