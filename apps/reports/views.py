from django.shortcuts import render
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ReportTemplate, GeneratedReport, Dashboard, DashboardWidget, ReportShare
from .serializers import (
    ReportTemplateSerializer, GeneratedReportSerializer, 
    DashboardSerializer, DashboardWidgetSerializer, ReportShareSerializer
)

# Import related models for report generation
from apps.audits.models import Audit, AuditFinding
from apps.clients.models import Client
from apps.finance.models import Invoice, Payment
from apps.employees.models import Employee


class ReportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReportTemplate.objects.filter(
            Q(is_public=True) | Q(created_by=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class GeneratedReportViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GeneratedReport.objects.filter(generated_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)


class DashboardViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dashboard.objects.filter(
            Q(is_public=True) | Q(owner=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DashboardWidget.objects.filter(
            dashboard__owner=self.request.user
        )


class AuditReportsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get audit reports data based on filters
        """
        # Get query parameters
        date_range = request.query_params.get('dateRange', '6M')
        standard = request.query_params.get('standard', 'all')
        status_filter = request.query_params.get('status', 'all')
        report_type = request.query_params.get('type', 'audit-summary')

        # Calculate date range
        end_date = timezone.now().date()
        if date_range == '1M':
            start_date = end_date - timedelta(days=30)
        elif date_range == '3M':
            start_date = end_date - timedelta(days=90)
        elif date_range == '6M':
            start_date = end_date - timedelta(days=180)
        elif date_range == '1Y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=180)  # Default to 6 months

        # Base queryset
        audits = Audit.objects.filter(
            created_at__date__range=[start_date, end_date]
        )

        # Apply filters
        if standard != 'all':
            audits = audits.filter(certification_standard__icontains=standard)
        
        if status_filter != 'all':
            audits = audits.filter(status=status_filter)

        if report_type == 'audit-summary':
            return self._get_audit_summary(audits, start_date, end_date)
        elif report_type == 'compliance-analysis':
            return self._get_compliance_analysis(audits)
        elif report_type == 'auditor-performance':
            return self._get_auditor_performance(audits)
        else:
            return Response({'error': 'Invalid report type'}, status=400)

    def _get_audit_summary(self, audits, start_date, end_date):
        """Get audit summary data"""
        total_audits = audits.count()
        completed_audits = audits.filter(status='COMPLETED').count()
        in_progress_audits = audits.filter(status='IN_PROGRESS').count()
        
        # Calculate average duration for completed audits
        completed = audits.filter(status='COMPLETED', end_date__isnull=False)
        avg_duration = 0
        if completed.exists():
            durations = [(audit.end_date - audit.start_date).days for audit in completed if audit.start_date]
            avg_duration = sum(durations) / len(durations) if durations else 0

        # Standards distribution
        standards_data = []
        standards = audits.values('certification_standard').annotate(count=Count('id')).order_by('-count')
        for standard in standards:
            if standard['certification_standard']:
                percentage = (standard['count'] / total_audits * 100) if total_audits > 0 else 0
                standards_data.append({
                    'standard': standard['certification_standard'],
                    'count': standard['count'],
                    'percentage': round(percentage, 1)
                })

        # Audit types
        audit_types = []
        types = audits.values('audit_type').annotate(count=Count('id'))
        for audit_type in types:
            if audit_type['audit_type']:
                audit_types.append({
                    'type': audit_type['audit_type'],
                    'count': audit_type['count']
                })

        # Monthly trends (last 6 months)
        monthly_trends = []
        for i in range(6):
            month_start = start_date + timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            month_audits = audits.filter(
                created_at__date__range=[month_start, month_end]
            ).count()
            monthly_trends.append({
                'month': month_start.strftime('%b'),
                'count': month_audits
            })

        return Response({
            'summary': {
                'total_audits': total_audits,
                'completed_audits': completed_audits,
                'in_progress_audits': in_progress_audits,
                'completion_rate': round((completed_audits / total_audits * 100) if total_audits > 0 else 0, 1),
                'avg_duration': round(avg_duration, 1)
            },
            'standards_distribution': standards_data,
            'audit_types': audit_types,
            'monthly_trends': monthly_trends
        })

    def _get_compliance_analysis(self, audits):
        """Get compliance analysis data"""
        total_audits = audits.count()
        
        # Get findings data
        findings = AuditFinding.objects.filter(audit__in=audits)
        minor_findings = findings.filter(severity='MINOR').count()
        major_findings = findings.filter(severity='MAJOR').count()
        
        # Calculate compliance rate
        audits_with_no_major_findings = audits.exclude(
            auditfinding__severity='MAJOR'
        ).count()
        compliance_rate = (audits_with_no_major_findings / total_audits * 100) if total_audits > 0 else 0

        # Compliance by standard
        compliance_by_standard = []
        standards = audits.values('certification_standard').distinct()
        for standard_data in standards:
            if standard_data['certification_standard']:
                standard_audits = audits.filter(certification_standard=standard_data['certification_standard'])
                standard_total = standard_audits.count()
                standard_compliant = standard_audits.exclude(auditfinding__severity='MAJOR').count()
                standard_rate = (standard_compliant / standard_total * 100) if standard_total > 0 else 0
                
                standard_findings = findings.filter(audit__certification_standard=standard_data['certification_standard']).count()
                
                compliance_by_standard.append({
                    'standard': standard_data['certification_standard'],
                    'compliance_rate': round(standard_rate, 1),
                    'total_findings': standard_findings
                })

        return Response({
            'summary': {
                'overall_compliance_rate': round(compliance_rate, 1),
                'minor_findings': minor_findings,
                'major_findings': major_findings,
                'total_audits': total_audits
            },
            'compliance_by_standard': compliance_by_standard
        })

    def _get_auditor_performance(self, audits):
        """Get auditor performance data"""
        # Get auditors who performed audits
        auditor_performance = []
        
        # Group by lead auditor
        auditors = audits.values('lead_auditor').annotate(
            audit_count=Count('id'),
            avg_duration=Avg('duration_days')
        ).filter(lead_auditor__isnull=False)

        for auditor_data in auditors:
            try:
                auditor = Employee.objects.get(id=auditor_data['lead_auditor'])
                auditor_audits = audits.filter(lead_auditor=auditor.id)
                
                # Calculate metrics
                total_audits = auditor_audits.count()
                completed_audits = auditor_audits.filter(status='COMPLETED').count()
                on_time_audits = auditor_audits.filter(
                    status='COMPLETED',
                    end_date__lte=timezone.now().date()
                ).count()
                
                on_time_rate = (on_time_audits / total_audits * 100) if total_audits > 0 else 0
                
                # Quality score based on findings (fewer findings = higher quality)
                total_findings = AuditFinding.objects.filter(audit__in=auditor_audits).count()
                quality_score = max(10 - (total_findings / total_audits), 0) if total_audits > 0 else 10
                
                # Client satisfaction (placeholder - would need actual feedback data)
                client_satisfaction = 4.5  # Placeholder
                
                auditor_performance.append({
                    'name': f"{auditor.first_name} {auditor.last_name}",
                    'audits_completed': total_audits,
                    'avg_duration': round(auditor_data['avg_duration'] or 0, 1),
                    'quality_score': round(quality_score, 1),
                    'client_satisfaction': client_satisfaction,
                    'on_time_rate': round(on_time_rate, 1)
                })
            except Employee.DoesNotExist:
                continue

        return Response({
            'auditor_performance': auditor_performance
        })


class FinancialReportsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get financial reports data based on filters
        """
        # Get query parameters
        date_range = request.query_params.get('dateRange', '6M')
        client_filter = request.query_params.get('client', 'all')
        standard_filter = request.query_params.get('standard', 'all')
        report_type = request.query_params.get('type', 'revenue-summary')

        # Calculate date range
        end_date = timezone.now().date()
        if date_range == '1M':
            start_date = end_date - timedelta(days=30)
        elif date_range == '3M':
            start_date = end_date - timedelta(days=90)
        elif date_range == '6M':
            start_date = end_date - timedelta(days=180)
        elif date_range == '1Y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=180)

        # Base querysets
        invoices = Invoice.objects.filter(
            invoice_date__range=[start_date, end_date]
        )
        
        # Apply filters
        if client_filter != 'all':
            invoices = invoices.filter(client_id=client_filter)

        if report_type == 'revenue-summary':
            return self._get_revenue_summary(invoices, start_date, end_date)
        elif report_type == 'payment-analysis':
            return self._get_payment_analysis(invoices)
        elif report_type == 'client-profitability':
            return self._get_client_profitability(invoices)
        elif report_type == 'revenue-forecast':
            return self._get_revenue_forecast(invoices)
        else:
            return Response({'error': 'Invalid report type'}, status=400)

    def _get_revenue_summary(self, invoices, start_date, end_date):
        """Get revenue summary data"""
        total_revenue = invoices.aggregate(total=Sum('amount'))['total'] or 0
        total_audits = invoices.count()
        avg_revenue_per_audit = total_revenue / total_audits if total_audits > 0 else 0
        
        # Payment status
        paid_amount = invoices.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
        collection_rate = (paid_amount / total_revenue * 100) if total_revenue > 0 else 0
        outstanding = total_revenue - paid_amount

        # Revenue by certification standard (from associated audits)
        revenue_by_standard = []
        for invoice in invoices.select_related('audit'):
            if hasattr(invoice, 'audit') and invoice.audit.certification_standard:
                # This would need proper model relationships
                pass

        # Monthly revenue trends
        monthly_trends = []
        current_date = start_date
        while current_date <= end_date:
            month_end = min(current_date + timedelta(days=30), end_date)
            month_revenue = invoices.filter(
                invoice_date__range=[current_date, month_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_trends.append({
                'month': current_date.strftime('%b %Y'),
                'revenue': month_revenue
            })
            current_date += timedelta(days=30)

        # Top clients by revenue
        client_revenue = invoices.values('client__name').annotate(
            total_revenue=Sum('amount'),
            audit_count=Count('id')
        ).order_by('-total_revenue')[:5]

        top_clients = []
        for client in client_revenue:
            avg_per_audit = client['total_revenue'] / client['audit_count'] if client['audit_count'] > 0 else 0
            # Determine payment status (simplified)
            client_invoices = invoices.filter(client__name=client['client__name'])
            paid_invoices = client_invoices.filter(status='PAID').count()
            total_invoices = client_invoices.count()
            
            if paid_invoices == total_invoices:
                payment_status = 'paid'
            elif paid_invoices > 0:
                payment_status = 'partial'
            else:
                payment_status = 'pending'

            top_clients.append({
                'client_name': client['client__name'] or 'Unknown Client',
                'total_revenue': client['total_revenue'],
                'audit_count': client['audit_count'],
                'avg_per_audit': avg_per_audit,
                'payment_status': payment_status
            })

        return Response({
            'summary': {
                'total_revenue': total_revenue,
                'avg_revenue_per_audit': round(avg_revenue_per_audit, 2),
                'collection_rate': round(collection_rate, 1),
                'outstanding_amount': outstanding
            },
            'monthly_trends': monthly_trends,
            'top_clients': top_clients
        })

    def _get_payment_analysis(self, invoices):
        """Get payment analysis data"""
        total_amount = invoices.aggregate(total=Sum('amount'))['total'] or 0
        paid_amount = invoices.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
        pending_amount = invoices.filter(status='PENDING').aggregate(total=Sum('amount'))['total'] or 0
        overdue_amount = invoices.filter(
            status='OVERDUE'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Payment timeline analysis
        current_date = timezone.now().date()
        on_time_invoices = invoices.filter(
            status='PAID',
            payment_date__lte=timezone.now().date()
        ).count()
        
        total_invoices = invoices.count()
        on_time_rate = (on_time_invoices / total_invoices * 100) if total_invoices > 0 else 0

        # Outstanding invoices
        outstanding_invoices = []
        overdue_invoices = invoices.filter(
            Q(status='PENDING') | Q(status='OVERDUE'),
            due_date__lt=current_date
        ).order_by('-due_date')[:10]

        for invoice in overdue_invoices:
            days_overdue = (current_date - invoice.due_date).days if invoice.due_date else 0
            outstanding_invoices.append({
                'invoice_number': invoice.invoice_number,
                'client_name': invoice.client.name if invoice.client else 'Unknown',
                'amount': invoice.amount,
                'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
                'days_overdue': max(days_overdue, 0),
                'status': invoice.status
            })

        return Response({
            'summary': {
                'total_amount': total_amount,
                'paid_amount': paid_amount,
                'pending_amount': pending_amount,
                'overdue_amount': overdue_amount,
                'collection_rate': round((paid_amount / total_amount * 100) if total_amount > 0 else 0, 1)
            },
            'payment_timeline': {
                'on_time_rate': round(on_time_rate, 1),
                'total_invoices': total_invoices
            },
            'outstanding_invoices': outstanding_invoices
        })

    def _get_client_profitability(self, invoices):
        """Get client profitability analysis"""
        client_profitability = []
        
        clients_revenue = invoices.values('client__name', 'client_id').annotate(
            total_revenue=Sum('amount')
        ).order_by('-total_revenue')

        for client_data in clients_revenue:
            if client_data['client__name']:
                # Calculate estimated costs (would need actual cost tracking)
                revenue = client_data['total_revenue']
                estimated_costs = revenue * 0.6  # Assuming 60% cost ratio
                profit = revenue - estimated_costs
                margin = (profit / revenue * 100) if revenue > 0 else 0

                client_profitability.append({
                    'client_name': client_data['client__name'],
                    'total_revenue': revenue,
                    'estimated_costs': estimated_costs,
                    'profit': profit,
                    'margin': round(margin, 1)
                })

        return Response({
            'client_profitability': client_profitability
        })

    def _get_revenue_forecast(self, invoices):
        """Get revenue forecast data"""
        # Simple forecast based on historical trends
        current_month_revenue = invoices.filter(
            invoice_date__month=timezone.now().month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Project next quarter (simplified)
        projected_q1 = current_month_revenue * 3 * 1.07  # 7% growth assumption
        
        return Response({
            'forecast': {
                'q1_2026_projection': projected_q1,
                'confidence_level': 75,
                'confirmed_pipeline': projected_q1 * 0.67,
                'pipeline_value': projected_q1 * 0.33
            },
            'monthly_projections': [
                {'month': 'January 2026', 'projected': projected_q1 / 3, 'confidence': 85},
                {'month': 'February 2026', 'projected': projected_q1 / 3 * 1.07, 'confidence': 78},
                {'month': 'March 2026', 'projected': projected_q1 / 3 * 1.03, 'confidence': 72}
            ]
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_summary_data(request):
    """Quick audit summary for dashboard widgets"""
    total_audits = Audit.objects.count()
    completed_audits = Audit.objects.filter(status='COMPLETED').count()
    in_progress_audits = Audit.objects.filter(status='IN_PROGRESS').count()
    
    return Response({
        'total_audits': total_audits,
        'completed': completed_audits,
        'in_progress': in_progress_audits,
        'completion_rate': round((completed_audits / total_audits * 100) if total_audits > 0 else 0, 1)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_summary_data(request):
    """Quick financial summary for dashboard widgets"""
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    monthly_revenue = Invoice.objects.filter(
        invoice_date__month=current_month,
        invoice_date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    paid_amount = Invoice.objects.filter(
        status='PAID',
        invoice_date__month=current_month,
        invoice_date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    outstanding = Invoice.objects.filter(
        status__in=['PENDING', 'OVERDUE']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    return Response({
        'monthly_revenue': monthly_revenue,
        'paid_amount': paid_amount,
        'outstanding_amount': outstanding,
        'collection_rate': round((paid_amount / monthly_revenue * 100) if monthly_revenue > 0 else 0, 1)
    })