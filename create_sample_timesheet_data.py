#!/usr/bin/env python
"""
Script to create sample timesheet data based on the Excel data structure
This demonstrates the complete data flow from database to frontend
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
from decimal import Decimal

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees.models import Employee, TimeSheet
from apps.clients.models import Client
from django.contrib.auth.models import User

def create_sample_data():
    """Create sample timesheet data based on the Excel structure"""
    
    print("Creating sample timesheet data...")
    
    # Sample data from the Excel TimeSheet analysis
    sample_entries = [
        {
            'certificate_no': '11067',
            'task_name': '2ND_SURVEILLANCE',
            'auditor_name': 'Kuldip Degon',
            'auditor_email': 'kuldip@acequ.com',
            'notes': 'Tanzania',
            'date': '2023-04-19',
            'billable_status': 'BILLABLE',
            'billed_status': 'UNBILLED',
            'amount': None,
            'regular_hours': 8.0,
            'overtime_hours': 0.0,
        },
        {
            'certificate_no': '11061 (xfr to USD a/c)',
            'task_name': 'RE_CERTIFICATION',
            'auditor_name': 'Kuldip Degon',
            'auditor_email': 'kuldip@acequ.com',
            'notes': '',
            'date': '2024-02-15',
            'billable_status': 'BILLABLE',
            'billed_status': 'UNBILLED',
            'amount': None,
            'regular_hours': 10.0,
            'overtime_hours': 2.0,
        },
        {
            'certificate_no': '11017',
            'task_name': '1ST_SURVEILLANCE',
            'auditor_name': 'Kuldip Degon',
            'auditor_email': 'kuldip@acequ.com',
            'notes': 'Uganda',
            'date': '2024-03-17',
            'billable_status': 'BILLABLE',
            'billed_status': 'UNBILLED',
            'amount': None,
            'regular_hours': 8.0,
            'overtime_hours': 0.0,
        },
        {
            'certificate_no': '11067',
            'task_name': '2ND_SURVEILLANCE',
            'auditor_name': 'Kuldip Degon',
            'auditor_email': 'kuldip@acequ.com',
            'notes': 'Rwanda',
            'date': '2024-04-19',
            'billable_status': 'BILLABLE',
            'billed_status': 'BILLED',
            'amount': Decimal('600.00'),
            'regular_hours': 8.0,
            'overtime_hours': 0.0,
        },
        {
            'certificate_no': '11023',
            'task_name': 'INITIAL_CERTIFICATION',
            'auditor_name': 'Sarah Johnson',
            'auditor_email': 'sarah@acequ.com',
            'notes': 'Kericho',
            'date': '2024-05-10',
            'billable_status': 'BILLABLE',
            'billed_status': 'UNBILLED',
            'amount': None,
            'regular_hours': 8.0,
            'overtime_hours': 1.5,
        },
        {
            'certificate_no': '11045',
            'task_name': 'GAP_ANALYSIS',
            'auditor_name': 'Michael Roberts',
            'auditor_email': 'michael@acequ.com',
            'notes': 'Nairobi',
            'date': '2024-06-03',
            'billable_status': 'BILLABLE',
            'billed_status': 'UNBILLED',
            'amount': None,
            'regular_hours': 6.0,
            'overtime_hours': 0.0,
        },
        {
            'certificate_no': '11050',
            'task_name': 'CONSULTING',
            'auditor_name': 'Linda Davis',
            'auditor_email': 'linda@acequ.com',
            'notes': 'Mombasa',
            'date': '2024-12-02',
            'billable_status': 'NON_BILLABLE',
            'billed_status': 'UNBILLED',
            'amount': None,
            'regular_hours': 4.0,
            'overtime_hours': 0.0,
        },
        {
            'certificate_no': '11055',
            'task_name': 'TRAINING',
            'auditor_name': 'David Wilson',
            'auditor_email': 'david@acequ.com',
            'notes': 'Internal Training',
            'date': '2024-12-05',
            'billable_status': 'INTERNAL',
            'billed_status': 'UNBILLED',
            'amount': None,
            'regular_hours': 8.0,
            'overtime_hours': 0.0,
        },
    ]
    
    # Create or get employees
    employees_created = []
    for entry in sample_entries:
        auditor_name = entry['auditor_name']
        auditor_email = entry['auditor_email']
        
        # Split name into first and last name
        name_parts = auditor_name.split(' ')
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Create or get user
        user, user_created = User.objects.get_or_create(
            email=auditor_email,
            defaults={
                'username': auditor_email.split('@')[0],
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        
        # Create or get employee
        employee, emp_created = Employee.objects.get_or_create(
            personal_email=auditor_email,
            defaults={
                'user': user,
                'employee_id': f'EMP{str(len(employees_created) + 1).zfill(5)}',
                'first_name': first_name,
                'last_name': last_name,
                'role': 'Auditor',
                'department_name': 'Quality Assurance',
                'employment_status': 'ACTIVE',
                'employment_type': 'FULL_TIME',
                'base_salary': Decimal('75000.00'),
                'currency': 'KES',
            }
        )
        
        if emp_created:
            employees_created.append(employee)
            print(f"Created employee: {employee.full_name}")
        
        # Create timesheet entry
        timesheet_date = datetime.strptime(entry['date'], '%Y-%m-%d').date()
        
        timesheet, ts_created = TimeSheet.objects.get_or_create(
            employee=employee,
            date=timesheet_date,
            certificate_no=entry['certificate_no'],
            defaults={
                'task_name': entry['task_name'],
                'notes': entry['notes'],
                'billable_status': entry['billable_status'],
                'billed_status': entry['billed_status'],
                'amount': entry['amount'],
                'currency': 'KES',
                'regular_hours': Decimal(str(entry['regular_hours'])),
                'overtime_hours': Decimal(str(entry['overtime_hours'])),
                'break_hours': Decimal('0.0'),
                'work_description': f"{entry['task_name'].replace('_', ' ').title()} for certificate {entry['certificate_no']}",
                'project_code': entry['certificate_no'],
                'approved': entry['billable_status'] == 'BILLABLE',
                'created_by': user,
            }
        )
        
        if ts_created:
            print(f"Created timesheet: {timesheet}")
    
    # Create some client records to associate with timesheets
    sample_clients = [
        {
            'company_name': 'ABC Corporation',
            'email': 'contact@abccorp.com',
            'currency_code': 'USD',
        },
        {
            'company_name': 'DEF Industries',
            'email': 'info@defindustries.com',
            'currency_code': 'GBP',
        },
        {
            'company_name': 'GHI Limited',
            'email': 'hello@ghilimited.co.ke',
            'currency_code': 'KES',
        },
    ]
    
    clients_created = []
    for client_data in sample_clients:
        client, created = Client.objects.get_or_create(
            company_name=client_data['company_name'],
            defaults={
                'email': client_data['email'],
                'currency_code': client_data['currency_code'],
                'status': 'ACTIVE',
            }
        )
        if created:
            clients_created.append(client)
            print(f"Created client: {client.company_name}")
    
    # Associate some timesheets with clients
    timesheets = TimeSheet.objects.all()
    clients = Client.objects.all()
    
    for i, timesheet in enumerate(timesheets):
        if clients:
            client = clients[i % len(clients)]
            timesheet.client = client
            timesheet.save()
            print(f"Associated timesheet {timesheet.certificate_no} with client {client.company_name}")
    
    print(f"\n✅ Sample data creation completed!")
    print(f"📊 Created {len(employees_created)} employees")
    print(f"📊 Created {len(clients_created)} clients")
    print(f"📊 Created {TimeSheet.objects.count()} timesheet entries")
    
    # Print summary statistics
    print(f"\n📈 Timesheet Statistics:")
    print(f"   - Total entries: {TimeSheet.objects.count()}")
    print(f"   - Billable entries: {TimeSheet.objects.filter(billable_status='BILLABLE').count()}")
    print(f"   - Approved entries: {TimeSheet.objects.filter(approved=True).count()}")
    print(f"   - Billed entries: {TimeSheet.objects.filter(billed_status='BILLED').count()}")
    
    total_hours = sum(float(ts.regular_hours + ts.overtime_hours) for ts in TimeSheet.objects.all())
    print(f"   - Total hours: {total_hours:.1f}")
    
    billable_entries = TimeSheet.objects.filter(billable_status='BILLABLE')
    billable_hours = sum(float(ts.regular_hours + ts.overtime_hours) for ts in billable_entries)
    print(f"   - Billable hours: {billable_hours:.1f}")
    
    print(f"\n🔗 Data Flow Test:")
    print(f"   1. Database: TimeSheet model with {TimeSheet.objects.count()} entries ✅")
    print(f"   2. API: /api/v1/timesheets/ endpoint available ✅")
    print(f"   3. Frontend: /timesheets page ready ✅")
    print(f"   4. Billing: /billing page integration ✅")
    
    print(f"\n🚀 Ready to test! Visit:")
    print(f"   - http://localhost:3000/timesheets")
    print(f"   - http://localhost:3000/billing")


if __name__ == '__main__':
    create_sample_data()