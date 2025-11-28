from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from .models import Payroll, PayrollEarning, PayrollDeduction
from .serializers import (
    PayrollSerializer, PayrollListSerializer,
    PayrollEarningSerializer, PayrollDeductionSerializer
)


class PayrollViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payroll model with CRUD operations.
    
    Endpoints:
    - GET /api/v1/payroll/ - List all payroll records
    - POST /api/v1/payroll/ - Create new payroll record
    - GET /api/v1/payroll/{id}/ - Get payroll details
    - PUT /api/v1/payroll/{id}/ - Update payroll
    - DELETE /api/v1/payroll/{id}/ - Delete payroll
    - GET /api/v1/payroll/stats/ - Get payroll statistics
    - POST /api/v1/payroll/{id}/approve/ - Approve payroll
    - POST /api/v1/payroll/{id}/process_payment/ - Process payment
    """
    queryset = Payroll.objects.select_related(
        'employee', 'approved_by', 'created_by'
    ).prefetch_related('earnings', 'deductions')
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'pay_period', 'employee', 'payment_method']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id', 'payment_reference']
    ordering_fields = ['start_date', 'end_date', 'net_pay', 'created_at']
    ordering = ['-start_date', '-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views."""
        if self.action == 'list':
            return PayrollListSerializer
        return PayrollSerializer
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get payroll statistics.
        Returns total payroll, pending, completed, and average salary.
        """
        queryset = self.get_queryset()
        
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date and end_date:
            queryset = queryset.filter(
                start_date__gte=start_date,
                end_date__lte=end_date
            )
        
        stats = {
            'total_payroll': queryset.aggregate(total=Sum('net_pay'))['total'] or 0,
            'pending_payroll': queryset.filter(
                Q(status='DRAFT') | Q(status='PENDING')
            ).aggregate(total=Sum('net_pay'))['total'] or 0,
            'completed_payroll': queryset.filter(
                status='PAID'
            ).aggregate(total=Sum('net_pay'))['total'] or 0,
            'average_salary': queryset.aggregate(avg=Avg('net_pay'))['avg'] or 0,
            'total_records': queryset.count(),
            'draft_count': queryset.filter(status='DRAFT').count(),
            'pending_count': queryset.filter(status='PENDING').count(),
            'approved_count': queryset.filter(status='APPROVED').count(),
            'paid_count': queryset.filter(status='PAID').count(),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a payroll record.
        Changes status from PENDING to APPROVED.
        """
        payroll = self.get_object()
        
        if payroll.status != 'PENDING':
            return Response(
                {'error': 'Only pending payroll records can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payroll.status = 'APPROVED'
        payroll.approved_by = request.user
        payroll.approved_date = timezone.now()
        payroll.save()
        
        serializer = self.get_serializer(payroll)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """
        Process payment for a payroll record.
        Changes status from APPROVED to PAID.
        """
        payroll = self.get_object()
        
        if payroll.status != 'APPROVED':
            return Response(
                {'error': 'Only approved payroll records can be processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payroll.status = 'PAID'
        payroll.processed_date = timezone.now()
        if not payroll.payment_date:
            payroll.payment_date = timezone.now().date()
        payroll.save()
        
        serializer = self.get_serializer(payroll)
        return Response(serializer.data)


class PayrollEarningViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PayrollEarning model.
    Manages additional earnings for payroll records.
    """
    queryset = PayrollEarning.objects.select_related('payroll', 'payroll__employee')
    serializer_class = PayrollEarningSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['payroll', 'earning_type']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']


class PayrollDeductionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PayrollDeduction model.
    Manages deductions for payroll records.
    """
    queryset = PayrollDeduction.objects.select_related('payroll', 'payroll__employee')
    serializer_class = PayrollDeductionSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['payroll', 'deduction_type']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

