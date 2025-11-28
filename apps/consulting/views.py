from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import (
    ConsultingProject, ProjectPhase, Deliverable, 
    ConsultantProfile, ClientHealth, ProjectRisk, 
    ClientFeedback, ProjectMilestone
)
from .serializers import (
    ConsultingProjectSerializer, ConsultantProfileSerializer,
    ClientHealthSerializer, ProjectRiskSerializer,
    ClientFeedbackSerializer, ProjectMilestoneSerializer,
    DashboardOverviewSerializer
)
from django.contrib.auth.models import User
from apps.business_development.models import ActivityLog
from apps.business_development.serializers import ActivityLogSerializer

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_overview(request):
    """
    Get consulting dashboard overview data
    GET /api/v1/consulting/dashboard/
    """
    # KPIs
    active_projects = ConsultingProject.objects.filter(status='IN_PROGRESS')
    active_projects_count = active_projects.count()
    
    total_revenue = ConsultingProject.objects.aggregate(total=Sum('budget'))['total'] or 0
    
    # Calculate utilization (mock logic for now as we don't have timesheets linked yet)
    consultants = ConsultantProfile.objects.all()
    avg_utilization = consultants.aggregate(avg=Avg('current_utilization'))['avg'] or 0
    
    # Revenue this quarter (mock logic)
    revenue_this_qtr = total_revenue / 4 if total_revenue else 0
    
    # Project Health
    on_track = active_projects.filter(risks__status='OPEN', risks__impact='HIGH').count()
    at_risk = active_projects.filter(Q(risks__status='OPEN') | Q(milestones__status='DELAYED')).distinct().count()
    behind = active_projects.filter(milestones__status='DELAYED').count()
    
    # Ensure numbers make sense (at_risk includes behind)
    on_track = active_projects_count - at_risk
    
    project_health = {
        'on_track': {'count': on_track, 'value': 0, 'percentage': (on_track/active_projects_count*100) if active_projects_count else 0},
        'at_risk': {'count': at_risk, 'value': 0, 'percentage': (at_risk/active_projects_count*100) if active_projects_count else 0},
        'behind': {'count': behind, 'value': 0, 'percentage': (behind/active_projects_count*100) if active_projects_count else 0},
    }
    
    # Upcoming Milestones
    today = timezone.now().date()
    next_30_days = today + timedelta(days=30)
    milestones = ProjectMilestone.objects.filter(
        due_date__range=[today, next_30_days]
    ).order_by('due_date')[:5]
    
    # Team Workload
    team_workload = []
    for consultant in consultants[:5]:
        team_workload.append({
            'name': consultant.user.get_full_name(),
            'projects': consultant.user.consulting_projects.count(),
            'utilization': consultant.current_utilization
        })
        
    data = {
        'active_projects_count': active_projects_count,
        'total_revenue': total_revenue,
        'utilization_rate': int(avg_utilization),
        'revenue_this_qtr': revenue_this_qtr,
        'project_health': project_health,
        'resource_allocation': {
            'billable': 78, 'admin': 12, 'training': 5, 'bench': 5 # Mock for now
        },
        'upcoming_milestones': ProjectMilestoneSerializer(milestones, many=True).data,
        'team_workload': team_workload,
        'revenue_trend': [], # To be implemented
        'client_portfolio': {} # To be implemented
    }
    
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def consultant_performance(request):
    """
    Get consultant performance data
    GET /api/v1/consulting/dashboard/consultants/
    """
    consultants = ConsultantProfile.objects.all()
    serializer = ConsultantProfileSerializer(consultants, many=True)
    
    # Calculate team KPIs
    avg_utilization = consultants.aggregate(avg=Avg('current_utilization'))['avg'] or 0
    total_billable = consultants.aggregate(total=Sum('billable_hours_ytd'))['total'] or 0
    avg_rating = consultants.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Mock skills capacity (since we don't have a granular skills model yet)
    skills_capacity = [
        { 'skill': "Strategy", 'capacity': 80, 'level': "High" },
        { 'skill': "Digital", 'capacity': 60, 'level': "Med" },
        { 'skill': "Process Opt", 'capacity': 80, 'level': "High" },
        { 'skill': "Data Analytics", 'capacity': 40, 'level': "Low" },
        { 'skill': "Change Mgmt", 'capacity': 60, 'level': "Med" },
        { 'skill': "IT Systems", 'capacity': 40, 'level': "Low" },
        { 'skill': "HR/Org Design", 'capacity': 40, 'level': "Low" },
    ]
    
    # Client Feedback
    feedbacks = ClientFeedback.objects.all().order_by('-date')[:5]
    feedback_data = ClientFeedbackSerializer(feedbacks, many=True).data
    
    return Response({
        'consultants': serializer.data,
        'kpis': {
            'avg_utilization': int(avg_utilization),
            'total_billable_hours': total_billable,
            'avg_client_rating': round(avg_rating, 1),
            'revenue_per_head': 0 # To be implemented
        },
        'skills_capacity': skills_capacity,
        'client_feedback': feedback_data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def client_health(request):
    """
    Get client health data
    GET /api/v1/consulting/dashboard/clients/
    """
    client_healths = ClientHealth.objects.all()
    at_risk_healths = client_healths.filter(health_score__lt=60)
    
    active_clients = client_healths.count()
    healthy_accounts = client_healths.filter(health_score__gte=70).count()
    at_risk_accounts = at_risk_healths.count()

    lifetime_value = ConsultingProject.objects.aggregate(Sum('budget'))['budget__sum'] or 0
    pipeline_value = ConsultingProject.objects.filter(status='PIPELINE').aggregate(Sum('budget'))['budget__sum'] or 0
    
    recent_activities = ActivityLog.objects.filter(
        client__in=client_healths.values_list('client', flat=True)
    ).order_by('-activity_date')[:10]
    
    return Response({
        'kpis': {
            'active_clients': active_clients,
            'healthy_accounts': healthy_accounts,
            'at_risk_accounts': at_risk_accounts,
            'lifetime_value': lifetime_value,
            'pipeline_value': pipeline_value
        },
        'client_matrix': ClientHealthSerializer(client_healths, many=True).data,
        'at_risk_clients': ClientHealthSerializer(at_risk_healths, many=True).data,
        'activity_log': ActivityLogSerializer(recent_activities, many=True).data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def delivery_excellence(request):
    """
    Get delivery excellence data
    GET /api/v1/consulting/dashboard/delivery/
    """
    projects = ConsultingProject.objects.all()
    
    # Calculate KPIs
    total_projects = projects.count()
    on_time = projects.filter(milestones__status='DELAYED').count()
    on_time_pct = ((total_projects - on_time) / total_projects * 100) if total_projects else 100
    
    # Client Satisfaction from Feedback
    feedbacks = ClientFeedback.objects.all()
    avg_satisfaction = feedbacks.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Client Satisfaction List
    client_satisfaction_list = []
    for feedback in feedbacks.select_related('project__client'):
        client_satisfaction_list.append({
            'client': feedback.project.client.name,
            'score': feedback.rating,
            'stars': feedback.rating
        })
        
    return Response({
        'kpis': {
            'on_time_delivery': int(on_time_pct),
            'on_budget': 82, # Mock
            'client_satisfaction': round(avg_satisfaction, 1),
            'quality_score': 92 # Mock
        },
        'projects': ConsultingProjectSerializer(projects, many=True).data,
        'risks': ProjectRiskSerializer(ProjectRisk.objects.filter(status='OPEN'), many=True).data,
        'client_satisfaction': client_satisfaction_list,
        'quality_scores': [
            { 'component': "Deliverable Quality", 'score': 94 },
            { 'component': "Documentation Quality", 'score': 91 },
            { 'component': "Process Adherence", 'score': 89 },
            { 'component': "Knowledge Transfer", 'score': 93 },
            { 'component': "Client Communication", 'score': 95 },
        ]
    })
