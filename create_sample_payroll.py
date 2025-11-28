"""
Script to create sample payroll data for testing
"""
import os
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees.models import Employee
from apps.finance.models import Payroll, PayrollEarning, PayrollDeduction
from django.contrib.auth.models import User

def create_sample_payroll():
    """Create sample payroll records"""
    
    # Get all employees
    employees = Employee.objects.all()[:5]  # Get first 5 employees
    
    if not employees:
        print("No employees found. Please create employees first.")
        return
    
    # Get or create a user for created_by
    user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    
    print(f"Creating payroll for {len(employees)} employees...")
    
    # Create payroll for current month
    start_date = date(2024, 11, 1)
    end_date = date(2024, 11, 30)
    payment_date = date(2024, 12, 5)
    
    for i, employee in enumerate(employees):
        # Calculate salary components
        base_salary = employee.base_salary or Decimal('5000.00')
        
        # Create payroll record
        payroll = Payroll.objects.create(
            employee=employee,
            pay_period='MONTHLY',
            start_date=start_date,
            end_date=end_date,
            base_salary=base_salary,
            gross_pay=base_salary,  # Will be updated after adding earnings
            total_deductions=Decimal('0.00'),  # Will be updated after adding deductions
            net_pay=base_salary,  # Will be updated
            currency='KES',
            status=['DRAFT', 'PENDING', 'APPROVED', 'PAID'][i % 4],  # Vary statuses
            payment_method='BANK_TRANSFER',
            payment_date=payment_date if i % 4 == 3 else None,  # Only paid ones have payment date
            created_by=user,
        )
        
        # Add some earnings (for some employees)
        if i % 2 == 0:
            PayrollEarning.objects.create(
                payroll=payroll,
                earning_type='BONUS',
                description='Performance Bonus',
                amount=Decimal('500.00')
            )
        
        if i % 3 == 0:
            PayrollEarning.objects.create(
                payroll=payroll,
                earning_type='OVERTIME',
                description='Overtime Hours',
                amount=Decimal('300.00')
            )
        
        # Add deductions
        # Tax (20% of gross)
        total_earnings = sum(e.amount for e in payroll.earnings.all())
        gross_pay = base_salary + total_earnings
        
        tax_amount = gross_pay * Decimal('0.20')
        PayrollDeduction.objects.create(
            payroll=payroll,
            deduction_type='TAX',
            description='Income Tax',
            amount=tax_amount
        )
        
        # Insurance
        PayrollDeduction.objects.create(
            payroll=payroll,
            deduction_type='INSURANCE',
            description='Health Insurance',
            amount=Decimal('200.00')
        )
        
        # Pension (for some employees)
        if i % 2 == 1:
            PayrollDeduction.objects.create(
                payroll=payroll,
                deduction_type='PENSION',
                description='Pension Contribution',
                amount=Decimal('300.00')
            )
        
        # Update payroll totals
        total_deductions = sum(d.amount for d in payroll.deductions.all())
        net_pay = gross_pay - total_deductions
        
        payroll.gross_pay = gross_pay
        payroll.total_deductions = total_deductions
        payroll.net_pay = net_pay
        payroll.save()
        
        print(f"Created payroll for {employee.first_name} {employee.last_name}: "
              f"Gross: {gross_pay}, Deductions: {total_deductions}, Net: {net_pay}, Status: {payroll.status}")
    
    print(f"\nSuccessfully created {len(employees)} payroll records!")

if __name__ == '__main__':
    create_sample_payroll()

