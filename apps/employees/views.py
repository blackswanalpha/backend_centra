from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.utils.dateparse import parse_date
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Employee, Department, Position, EmployeeSkill, PerformanceReview, TimeSheet
from .serializers import (
    EmployeeSerializer, 
    DepartmentSerializer, 
    PositionSerializer,
    EmployeeSkillSerializer,
    PerformanceReviewSerializer,
    TimeSheetSerializer,
    TimeSheetSummarySerializer
)
from apps.audits.models import Audit


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Department model with CRUD operations.
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class PositionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Position model with CRUD operations.
    """
    queryset = Position.objects.select_related('department').all()
    serializer_class = PositionSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'level', 'created_at']
    ordering = ['department', 'level', 'title']


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Employee model with CRUD operations.
    Supports filtering, searching, and ordering.
    """
    queryset = Employee.objects.select_related('user', 'position', 'position__department').prefetch_related('skills').all()
    serializer_class = EmployeeSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employment_status', 'employment_type', 'role', 'department_name']
    search_fields = ['first_name', 'last_name', 'employee_id', 'personal_email', 'phone_number', 'department_name']
    ordering_fields = ['first_name', 'last_name', 'hire_date', 'created_at', 'employment_status']
    ordering = ['first_name', 'last_name']

    def perform_create(self, serializer):
        """
        Create employee with auto-generated employee_id and user account
        """
        # Generate employee_id
        last_employee = Employee.objects.order_by('-id').first()
        if last_employee and last_employee.employee_id:
            try:
                last_id = int(last_employee.employee_id.replace('EMP', ''))
                new_id = f"EMP{str(last_id + 1).zfill(5)}"
            except ValueError:
                new_id = "EMP00001"
        else:
            new_id = "EMP00001"
        
        # Create user account
        email = serializer.validated_data.get('personal_email', '')
        first_name = serializer.validated_data.get('first_name', '')
        last_name = serializer.validated_data.get('last_name', '')
        
        # Generate username from email or name
        if email:
            username = email.split('@')[0]
        else:
            username = f"{first_name.lower()}.{last_name.lower()}"
        
        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create user with random password
        import secrets
        import string
        # Generate random password
        alphabet = string.ascii_letters + string.digits + string.punctuation
        random_password = ''.join(secrets.choice(alphabet) for i in range(16))

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=random_password
        )
        
        # Save employee with generated employee_id and user
        serializer.save(employee_id=new_id, user=user)

    @action(detail=True, methods=['get'])
    def skills(self, request, pk=None):
        """Get all skills for an employee"""
        employee = self.get_object()
        skills = employee.skills.all()
        serializer = EmployeeSkillSerializer(skills, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get employee statistics"""
        total = Employee.objects.count()
        active = Employee.objects.filter(employment_status='ACTIVE').count()
        inactive = Employee.objects.filter(employment_status='INACTIVE').count()
        on_leave = Employee.objects.filter(employment_status='ON_LEAVE').count()
        terminated = Employee.objects.filter(employment_status='TERMINATED').count()
        
        return Response({
            'total': total,
            'active': active,
            'inactive': inactive,
            'onLeave': on_leave,
            'terminated': terminated
        })


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for EmployeeSkill model with CRUD operations.
    """
    queryset = EmployeeSkill.objects.select_related('employee').all()
    serializer_class = EmployeeSkillSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'proficiency_level', 'certified']
    search_fields = ['skill_name']
    ordering_fields = ['skill_name', 'proficiency_level', 'years_of_experience']
    ordering = ['skill_name']


class TimeSheetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TimeSheet model with comprehensive filtering and analytics
    Matches the Excel data structure for audit time tracking
    """
    queryset = TimeSheet.objects.select_related(
        'employee', 'client', 'approved_by', 'created_by'
    ).order_by('-date', '-created_at')
    serializer_class = TimeSheetSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'employee', 'client', 'task_name', 'billable_status', 'billed_status',
        'approved', 'certificate_no', 'project_code'
    ]
    search_fields = [
        'certificate_no', 'work_description', 'notes', 'project_code',
        'employee__first_name', 'employee__last_name', 'client__company_name'
    ]
    ordering_fields = ['date', 'created_at', 'regular_hours', 'amount', 'employee__first_name']
    ordering = ['-date', '-created_at']

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()
        
        # Date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                date_from = parse_date(date_from)
                queryset = queryset.filter(date__gte=date_from)
            except (ValueError, TypeError):
                pass
        
        if date_to:
            try:
                date_to = parse_date(date_to)
                queryset = queryset.filter(date__lte=date_to)
            except (ValueError, TypeError):
                pass
        
        # Filter by current user if requested
        current_user_only = self.request.query_params.get('current_user_only')
        if current_user_only and current_user_only.lower() == 'true':
            try:
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get timesheet statistics and summaries for billing and reporting"""
        queryset = self.get_queryset()
        
        # Date range for stats
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            # Default to current month
            today = timezone.now().date()
            date_from = today.replace(day=1)
        else:
            date_from = parse_date(date_from)
        
        if not date_to:
            # Default to end of current month
            today = timezone.now().date()
            if today.month == 12:
                date_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                date_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        else:
            date_to = parse_date(date_to)
        
        # Filter by date range
        queryset = queryset.filter(date__gte=date_from, date__lte=date_to)
        
        # Basic aggregations
        total_entries = queryset.count()
        total_hours = queryset.aggregate(
            regular=Sum('regular_hours'),
            overtime=Sum('overtime_hours')
        )
        
        regular_hours = total_hours['regular'] or Decimal('0')
        overtime_hours = total_hours['overtime'] or Decimal('0')
        total_hours_sum = regular_hours + overtime_hours
        
        # Billable hours
        billable_queryset = queryset.filter(billable_status='BILLABLE')
        billable_hours = billable_queryset.aggregate(
            regular=Sum('regular_hours'),
            overtime=Sum('overtime_hours')
        )
        billable_regular = billable_hours['regular'] or Decimal('0')
        billable_overtime = billable_hours['overtime'] or Decimal('0')
        total_billable_hours = billable_regular + billable_overtime
        
        # Calculate amounts
        total_amount = queryset.aggregate(amount_sum=Sum('amount'))['amount_sum'] or Decimal('0')
        
        # If no stored amounts, calculate from hours
        if total_amount == 0:
            hourly_rate = Decimal('75.0')  # Default rate
            total_amount = (regular_hours * hourly_rate) + (overtime_hours * hourly_rate * Decimal('1.5'))
        
        # Breakdown by status
        by_billable_status = {}
        for status_choice in TimeSheet.BILLABLE_STATUS_CHOICES:
            status_code = status_choice[0]
            status_count = queryset.filter(billable_status=status_code).count()
            by_billable_status[status_code] = status_count
        
        by_billed_status = {}
        for status_choice in TimeSheet.BILLED_STATUS_CHOICES:
            status_code = status_choice[0]
            status_count = queryset.filter(billed_status=status_code).count()
            by_billed_status[status_code] = status_count
        
        by_task_type = {}
        for task_choice in TimeSheet.TASK_TYPE_CHOICES:
            task_code = task_choice[0]
            task_count = queryset.filter(task_name=task_code).count()
            by_task_type[task_code] = task_count
        
        stats_data = {
            'total_entries': total_entries,
            'total_hours': total_hours_sum,
            'billable_hours': total_billable_hours,
            'total_amount': total_amount,
            'by_billable_status': by_billable_status,
            'by_billed_status': by_billed_status,
            'by_task_type': by_task_type,
            'date_from': date_from,
            'date_to': date_to,
        }
        
        serializer = TimeSheetSummarySerializer(data=stats_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """Approve multiple timesheet entries for billing"""
        timesheet_ids = request.data.get('ids', [])
        
        if not timesheet_ids:
            return Response(
                {'error': 'No timesheet IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timesheets = self.get_queryset().filter(id__in=timesheet_ids)
        approved_count = 0
        
        for timesheet in timesheets:
            if not timesheet.approved:
                timesheet.approved = True
                timesheet.approved_by = request.user
                timesheet.approved_at = timezone.now()
                timesheet.save()
                approved_count += 1
        
        return Response({
            'success': True,
            'message': f'Approved {approved_count} timesheet entries',
            'approved_count': approved_count
        })

    @action(detail=False, methods=['post'])
    def bulk_update_billing(self, request):
        """Update billing status for multiple timesheet entries"""
        timesheet_ids = request.data.get('ids', [])
        billed_status = request.data.get('billed_status', 'BILLED')
        
        if not timesheet_ids:
            return Response(
                {'error': 'No timesheet IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timesheets = self.get_queryset().filter(id__in=timesheet_ids)
        updated_count = timesheets.update(billed_status=billed_status)
        
        return Response({
            'success': True,
            'message': f'Updated billing status for {updated_count} entries',
            'updated_count': updated_count
        })


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for PerformanceReview model"""
    queryset = PerformanceReview.objects.select_related('employee', 'reviewer')
    serializer_class = PerformanceReviewSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'reviewer', 'review_type', 'status', 'is_finalized']
    search_fields = ['employee__first_name', 'employee__last_name', 'reviewer__first_name']
    ordering_fields = ['review_period_end', 'overall_rating', 'created_at']
    ordering = ['-review_period_end']


@api_view(['GET'])
@permission_classes([AllowAny])
def auditor_availability_view(request):
    """
    Get auditor availability for a specific date range.
    
    Query Parameters:
    - start_date: Start date for availability check (YYYY-MM-DD)
    - end_date: End date for availability check (YYYY-MM-DD)
    
    Returns:
    List of auditors with their availability status for the given date range.
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Get all auditors (employees with role containing 'auditor')
    auditors = Employee.objects.filter(
        Q(role__icontains='auditor') | Q(role__icontains='lead'),
        employment_status='ACTIVE'
    ).select_related('user')
    
    availability_data = []
    
    for auditor in auditors:
        # Basic auditor information
        auditor_data = {
            'auditor': {
                'id': auditor.id,
                'name': auditor.full_name,
                'email': auditor.user.email if auditor.user else auditor.personal_email,
                'role': auditor.role,
                'certifications': auditor.certifications,
                'experience_years': auditor.experience_years,
                'utilization': auditor.utilization
            },
            'availability': 'available',  # Default to available
            'conflicts': [],
            'workload_percentage': auditor.utilization
        }
        
        # If date range is provided, check for conflicts
        if start_date and end_date:
            try:
                start_dt = parse_date(start_date)
                end_dt = parse_date(end_date)
                
                if start_dt and end_dt:
                    # Check for existing audits in the date range
                    conflicting_audits = Audit.objects.filter(
                        Q(lead_auditor=auditor.user) | Q(auditors=auditor.user),
                        planned_start_date__lte=end_dt,
                        planned_end_date__gte=start_dt,
                        status__in=['PLANNED', 'IN_PROGRESS']
                    ).distinct()

                    # Check timesheet data
                    conflicting_timesheets = TimeSheet.objects.filter(
                        employee=auditor,
                        date__range=[start_dt, end_dt],
                        task_name__in=['INITIAL_CERTIFICATION', 'RE_CERTIFICATION', '1ST_SURVEILLANCE', '2ND_SURVEILLANCE']
                    )
                    
                    if conflicting_audits.exists() or conflicting_timesheets.exists():
                        auditor_data['availability'] = 'busy'
                        
                        # Add audit conflicts
                        for audit in conflicting_audits:
                            auditor_data['conflicts'].append({
                                'date': f"{audit.planned_start_date} to {audit.planned_end_date}",
                                'task': f"Audit: {audit.title}",
                                'notes': f"Role: {'Lead Auditor' if audit.lead_auditor == auditor.user else 'Auditor'}",
                                'start_date': audit.planned_start_date.isoformat(),
                                'end_date': audit.planned_end_date.isoformat(),
                                'type': 'audit'
                            })

                        # Add timesheet conflicts
                        for ts in conflicting_timesheets:
                            auditor_data['conflicts'].append({
                                'date': ts.date.isoformat(),
                                'task': ts.get_task_name_display(),
                                'notes': ts.notes or 'Scheduled audit activity',
                                'start_date': ts.date.isoformat(),
                                'end_date': ts.date.isoformat(),
                                'type': 'timesheet'
                            })
                    
                    # Calculate workload based on scheduled days
                    total_days = (end_dt - start_dt).days + 1
                    
                    # Calculate busy days from audits
                    audit_busy_days = set()
                    for audit in conflicting_audits:
                        current = max(audit.planned_start_date, start_dt.date())
                        end = min(audit.planned_end_date, end_dt.date())
                        while current <= end:
                            audit_busy_days.add(current)
                            current += timedelta(days=1)
                            
                    # Calculate busy days from timesheets
                    timesheet_busy_days = set(ts.date for ts in conflicting_timesheets)
                    
                    all_busy_days = audit_busy_days.union(timesheet_busy_days)
                    busy_days_count = len(all_busy_days)
                    
                    if total_days > 0:
                        workload_percentage = min(100, int((busy_days_count / total_days) * 100))
                        auditor_data['workload_percentage'] = workload_percentage
                        
                        # Determine availability based on workload
                        if workload_percentage >= 80:
                            auditor_data['availability'] = 'busy'
                        elif workload_percentage >= 50:
                            auditor_data['availability'] = 'partially_available'
                        else:
                            auditor_data['availability'] = 'available'
                            
            except (ValueError, TypeError) as e:
                # Invalid date format, return default availability
                pass
        
        availability_data.append(auditor_data)
    
    # Sort by availability (available first, then partially available, then busy)
    availability_order = {'available': 0, 'partially_available': 1, 'busy': 2}
    availability_data.sort(key=lambda x: (availability_order.get(x['availability'], 3), x['auditor']['name']))
    
    return Response({
        'success': True,
        'data': availability_data,
        'summary': {
            'total_auditors': len(availability_data),
            'available': len([a for a in availability_data if a['availability'] == 'available']),
            'partially_available': len([a for a in availability_data if a['availability'] == 'partially_available']),
            'busy': len([a for a in availability_data if a['availability'] == 'busy']),
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    })

