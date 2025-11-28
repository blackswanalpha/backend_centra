from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Payroll, PayrollEarning, PayrollDeduction
from apps.employees.models import Employee


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (minimal)."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
        read_only_fields = ['id', 'username', 'email']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class EmployeeMinimalSerializer(serializers.ModelSerializer):
    """Minimal employee serializer for payroll."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = ['id', 'employee_id', 'first_name', 'last_name', 'full_name', 'department_name']
        read_only_fields = ['id', 'employee_id', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class PayrollEarningSerializer(serializers.ModelSerializer):
    """Serializer for PayrollEarning model."""
    
    class Meta:
        model = PayrollEarning
        fields = ['id', 'payroll', 'earning_type', 'description', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']


class PayrollDeductionSerializer(serializers.ModelSerializer):
    """Serializer for PayrollDeduction model."""
    
    class Meta:
        model = PayrollDeduction
        fields = ['id', 'payroll', 'deduction_type', 'description', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']


class PayrollListSerializer(serializers.ModelSerializer):
    """Serializer for Payroll list view (minimal data)."""
    employee_name = serializers.SerializerMethodField()
    employee_id_display = serializers.CharField(source='employee.employee_id', read_only=True)
    department = serializers.CharField(source='employee.department_name', read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_display', 'department',
            'pay_period', 'start_date', 'end_date',
            'base_salary', 'gross_pay', 'total_deductions', 'net_pay', 'currency',
            'status', 'payment_method', 'payment_date',
            'approved_by_name', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
    
    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip() or obj.approved_by.username
        return None
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None


class PayrollSerializer(serializers.ModelSerializer):
    """Serializer for Payroll model with full details."""
    employee_name = serializers.SerializerMethodField()
    employee_data = EmployeeMinimalSerializer(source='employee', read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    approved_by_data = UserSerializer(source='approved_by', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    created_by_data = UserSerializer(source='created_by', read_only=True)
    earnings = PayrollEarningSerializer(many=True, read_only=True)
    deductions = PayrollDeductionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'employee', 'employee_name', 'employee_data',
            'pay_period', 'start_date', 'end_date',
            'base_salary', 'gross_pay', 'total_deductions', 'net_pay', 'currency',
            'status', 'approved_by', 'approved_by_name', 'approved_by_data',
            'approved_date', 'payment_method', 'payment_date', 'processed_date',
            'payment_reference', 'notes',
            'created_by', 'created_by_name', 'created_by_data',
            'created_at', 'updated_at',
            'earnings', 'deductions'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}".strip()
    
    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip() or obj.approved_by.username
        return None
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
    
    def create(self, validated_data):
        # Set created_by from request user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)

