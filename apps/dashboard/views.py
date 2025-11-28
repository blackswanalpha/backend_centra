"""
Dashboard Views
Provides aggregated metrics and analytics for various dashboards
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.audits.models import Audit
from apps.clients.models import Client
from apps.employees.models import Employee
from apps.business_development.models import Opportunity, Contract
from apps.finance.models import Payroll
from apps.tasks.models import Task


@api_view(['GET'])
@permission_classes([AllowAny])  # Change to IsAuthenticated in production
def overview_dashboard(request):
    """
    Main dashboard overview metrics
    GET /api/v1/dashboard/overview/
    """
    try:
        # Calculate date ranges
        today = timezone.now().date()
        last_month = today - timedelta(days=30)

        # Get audit metrics
        total_audits = Audit.objects.count()
        active_audits = Audit.objects.filter(
            status__in=['PLANNED', 'IN_PROGRESS']
        ).count()

        # Calculate revenue from active contracts
        active_contracts = Contract.objects.filter(status='ACTIVE')
        actual_revenue = active_contracts.aggregate(
            total=Sum('contract_value')
        )['total'] or 0

        # Revenue from contracts signed this month
        contracts_this_month = Contract.objects.filter(
            company_signed_date__gte=last_month,
            status='ACTIVE'
        )
        completed_this_month = contracts_this_month.aggregate(
            total=Sum('contract_value')
        )['total'] or 0

        # Overdue invoices (mock data - implement when invoice model exists)
        overdue_invoices = 0

        # Calculate trends (mock - implement proper historical comparison)
        revenue_trend = 8.5
        completed_revenue_trend = 15.2
        active_audits_trend = 2.0
        overdue_invoices_trend = -2.0

        return Response({
            'actual_revenue': float(actual_revenue),
            'completed_revenue': float(completed_this_month),
            'active_audits': active_audits,
            'overdue_invoices': overdue_invoices,
            'revenue_trend': revenue_trend,
            'completed_revenue_trend': completed_revenue_trend,
            'active_audits_trend': active_audits_trend,
            'overdue_invoices_trend': overdue_invoices_trend,
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def financial_dashboard(request):
    """
    Financial dashboard metrics
    GET /api/v1/dashboard/financial/
    """
    try:
        # Get active and completed contracts for revenue calculation
        active_contracts = Contract.objects.filter(status__in=['ACTIVE', 'COMPLETED'])

        revenue = active_contracts.aggregate(
            total=Sum('contract_value')
        )['total'] or 0

        # Mock data for billed, collected, and A/R
        # Implement when invoice/payment models exist
        billed = float(revenue) * 0.95
        collected = float(revenue) * 0.90
        accounts_receivable = billed - collected

        # AR Aging breakdown
        ar_aging = [
            {'range': '0-30 days', 'amount': accounts_receivable * 0.60, 'percentage': 60, 'critical': False},
            {'range': '31-60 days', 'amount': accounts_receivable * 0.27, 'percentage': 27, 'critical': False},
            {'range': '61-90 days', 'amount': accounts_receivable * 0.09, 'percentage': 9, 'critical': False},
            {'range': '90+ days', 'amount': accounts_receivable * 0.04, 'percentage': 4, 'critical': True},
        ]

        return Response({
            'revenue': float(revenue),
            'billed': billed,
            'collected': collected,
            'accounts_receivable': accounts_receivable,
            'revenue_trend': 5.0,
            'billed_trend': 3.0,
            'collected_trend': 2.0,
            'ar_trend': 8.0,
            'ar_aging': ar_aging,
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def sales_dashboard(request):
    """
    Sales pipeline metrics
    GET /api/v1/dashboard/sales/
    """
    try:
        # Get opportunities by status (not stage)
        opportunities = Opportunity.objects.all()

        pipeline_stages = []
        stages = ['PROSPECTING', 'QUALIFICATION', 'PROPOSAL', 'NEGOTIATION', 'CLOSED_WON']
        stage_names = ['Leads', 'Qualified', 'Proposal', 'Negotiation', 'Closed-Won']

        total_value = opportunities.aggregate(total=Sum('estimated_value'))['total'] or 1

        for stage_code, stage_name in zip(stages, stage_names):
            stage_opps = opportunities.filter(status=stage_code)
            count = stage_opps.count()
            value = stage_opps.aggregate(total=Sum('estimated_value'))['total'] or 0
            percentage = int((float(value) / float(total_value)) * 100) if total_value > 0 else 0

            pipeline_stages.append({
                'stage': stage_name,
                'count': count,
                'value': float(value),
                'percentage': percentage,
            })

        return Response({
            'pipeline_stages': pipeline_stages,
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def auditor_dashboard(request):
    """
    Auditor performance metrics
    GET /api/v1/dashboard/auditors/
    """
    try:
        # Get auditor (employee) metrics
        auditors = Employee.objects.filter(
            position__title__icontains='auditor'
        )

        # Mock data - implement when proper auditor tracking exists
        auditor_performance = []
        for auditor in auditors[:5]:  # Top 5 auditors
            auditor_performance.append({
                'name': f"{auditor.first_name} {auditor.last_name}",
                'audits_completed': 12,
                'utilization_rate': 85.0,
                'average_rating': 4.5,
            })

        return Response({
            'auditor_performance': auditor_performance,
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def client_dashboard(request):
    """
    Client health metrics
    GET /api/v1/dashboard/clients/
    """
    try:
        # Get client metrics
        total_clients = Client.objects.count()
        active_clients = Client.objects.filter(status='ACTIVE').count()

        # Mock data for client health scores
        client_health = []
        clients = Client.objects.filter(status='ACTIVE')[:10]

        for client in clients:
            client_health.append({
                'name': client.name,
                'health_score': 85,
                'last_audit': '2024-01-15',
                'next_audit': '2024-04-15',
            })

        return Response({
            'total_clients': total_clients,
            'active_clients': active_clients,
            'client_health': client_health,
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def operations_dashboard(request):
    """
    Operations efficiency metrics
    GET /api/v1/dashboard/operations/
    """
    try:
        # Get task metrics
        total_tasks = Task.objects.count()
        completed_tasks = Task.objects.filter(status='COMPLETED').count()
        overdue_tasks = Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['TODO', 'IN_PROGRESS']
        ).count()

        # Calculate completion rate
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return Response({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'completion_rate': round(completion_rate, 1),
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def activity_dashboard(request):
    """
    Activity feed
    GET /api/v1/dashboard/activity/
    """
    try:
        limit = int(request.query_params.get('limit', 20))

        # Mock activity data - implement when activity log model exists
        activities = [
            {
                'id': 1,
                'type': 'audit_completed',
                'description': 'ISO 9001 audit completed for Acme Corp',
                'timestamp': timezone.now().isoformat(),
                'user': 'John Doe',
            },
            {
                'id': 2,
                'type': 'client_added',
                'description': 'New client TechStart Inc added',
                'timestamp': (timezone.now() - timedelta(hours=2)).isoformat(),
                'user': 'Jane Smith',
            },
        ]

        return Response(activities[:limit])
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def goals_dashboard(request):
    """
    Goals and KPIs
    GET /api/v1/dashboard/goals/
    """
    try:
        # Mock goals data - implement when goals model exists
        goals = [
            {
                'name': 'Quarterly Revenue',
                'target': 500000,
                'current': 425000,
                'percentage': 85,
                'status': 'on_track',
            },
            {
                'name': 'Client Satisfaction',
                'target': 95,
                'current': 92,
                'percentage': 97,
                'status': 'on_track',
            },
            {
                'name': 'Audit Completion Rate',
                'target': 100,
                'current': 88,
                'percentage': 88,
                'status': 'at_risk',
            },
        ]

        return Response({
            'goals': goals,
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

