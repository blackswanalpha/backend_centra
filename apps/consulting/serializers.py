from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ConsultingProject, ProjectPhase, Deliverable, 
    ConsultantProfile, ClientHealth, ProjectRisk, 
    ClientFeedback, ProjectMilestone
)
from apps.clients.serializers import ClientSerializer

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']
        
    def get_full_name(self, obj):
        return obj.get_full_name()

class ConsultantProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ConsultantProfile
        fields = '__all__'

class ProjectRiskSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    
    class Meta:
        model = ProjectRisk
        fields = '__all__'

class ClientFeedbackSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    client_name = serializers.CharField(source='project.client.name', read_only=True)
    
    class Meta:
        model = ClientFeedback
        fields = '__all__'

class ProjectMilestoneSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    
    class Meta:
        model = ProjectMilestone
        fields = '__all__'

class ClientHealthSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    industry = serializers.CharField(source='client.industry', read_only=True)
    account_manager_name = serializers.CharField(source='account_manager.get_full_name', read_only=True)
    revenue = serializers.SerializerMethodField()
    active_project = serializers.SerializerMethodField()
    
    class Meta:
        model = ClientHealth
        fields = '__all__'
        
    def get_revenue(self, obj):
        from django.db.models import Sum
        return obj.client.consulting_projects.aggregate(total=Sum('budget'))['total'] or 0

    def get_active_project(self, obj):
        project = obj.client.consulting_projects.filter(status='IN_PROGRESS').order_by('-start_date').first()
        if project:
            return {
                'name': project.project_name,
                'value': project.budget,
                'currency': project.currency
            }
        return None

class ConsultingProjectSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    project_manager_name = serializers.CharField(source='project_manager.get_full_name', read_only=True)
    health_status = serializers.SerializerMethodField()
    timeline_status = serializers.SerializerMethodField()
    budget_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ConsultingProject
        fields = '__all__'
        
    def get_health_status(self, obj):
        # Simple logic to determine health based on risks and milestones
        open_risks = obj.risks.filter(status='OPEN', impact='HIGH').count()
        delayed_milestones = obj.milestones.filter(status='DELAYED').count()
        
        if open_risks > 0 or delayed_milestones > 0:
            return 'AT_RISK'
        return 'ON_TRACK'

    def get_timeline_status(self, obj):
        if obj.milestones.filter(status='DELAYED').exists():
            return 'behind'
        return 'on_track'

    def get_budget_status(self, obj):
        # Mock logic as we don't have actuals yet
        return 'on_budget'

class DashboardOverviewSerializer(serializers.Serializer):
    active_projects_count = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    utilization_rate = serializers.IntegerField()
    revenue_this_qtr = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    project_health = serializers.DictField()
    resource_allocation = serializers.DictField()
    upcoming_milestones = ProjectMilestoneSerializer(many=True)
    team_workload = serializers.ListField()
    revenue_trend = serializers.ListField()
    client_portfolio = serializers.DictField()
