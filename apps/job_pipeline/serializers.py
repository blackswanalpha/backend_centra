from rest_framework import serializers
from django.contrib.auth.models import User
from .models import JobPipeline, PipelineStageTransition, PipelineMilestone
from apps.business_development.models import Lead, Opportunity, Contract
from apps.audits.models import Audit


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']


class LeadBasicSerializer(serializers.ModelSerializer):
    """Basic lead serializer for pipeline"""
    class Meta:
        model = Lead
        fields = ['id', 'company_name', 'contact_person', 'email', 'status', 'estimated_value', 'currency']


class OpportunityBasicSerializer(serializers.ModelSerializer):
    """Basic opportunity serializer for pipeline"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = Opportunity
        fields = ['id', 'title', 'client_name', 'status', 'estimated_value', 'currency', 'probability']


class ContractBasicSerializer(serializers.ModelSerializer):
    """Basic contract serializer for pipeline"""
    class Meta:
        model = Contract
        fields = ['id', 'contract_number', 'client_organization', 'status', 'contract_value', 'currency', 'start_date', 'end_date']


class AuditBasicSerializer(serializers.ModelSerializer):
    """Basic audit serializer for pipeline"""
    lead_auditor_name = serializers.CharField(source='lead_auditor.get_full_name', read_only=True)
    
    class Meta:
        model = Audit
        fields = ['id', 'audit_number', 'title', 'audit_type', 'status', 'planned_start_date', 'planned_end_date', 'lead_auditor_name']


class PipelineMilestoneSerializer(serializers.ModelSerializer):
    """Serializer for pipeline milestones"""
    assigned_to = UserBasicSerializer(read_only=True)
    assigned_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = PipelineMilestone
        fields = [
            'id', 'milestone_type', 'title', 'description', 'due_date', 'completed_date',
            'is_completed', 'is_critical', 'assigned_to', 'assigned_to_id', 
            'is_overdue', 'days_remaining', 'created_at', 'updated_at'
        ]


class PipelineStageTransitionSerializer(serializers.ModelSerializer):
    """Serializer for stage transitions"""
    transitioned_by = UserBasicSerializer(read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.pipeline_id', read_only=True)
    
    class Meta:
        model = PipelineStageTransition
        fields = [
            'id', 'pipeline', 'pipeline_name', 'from_stage', 'to_stage', 
            'transitioned_at', 'transitioned_by', 'notes'
        ]


class JobPipelineSerializer(serializers.ModelSerializer):
    """Main job pipeline serializer"""
    owner = UserBasicSerializer(read_only=True)
    owner_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    created_by = UserBasicSerializer(read_only=True)
    stage_progress_percentage = serializers.IntegerField(read_only=True)
    days_in_current_stage = serializers.IntegerField(read_only=True)
    
    # Related objects count
    audits_count = serializers.SerializerMethodField()
    milestones_count = serializers.SerializerMethodField()
    overdue_milestones_count = serializers.SerializerMethodField()
    
    # Current stage info
    next_milestone = serializers.CharField(read_only=True)
    next_milestone_date = serializers.DateField(read_only=True)
    
    class Meta:
        model = JobPipeline
        fields = [
            'id', 'pipeline_id', 'client_name', 'service_description', 'estimated_value', 'currency',
            'current_stage', 'status', 'stage_progress_percentage', 'days_in_current_stage',
            'lead_created_date', 'opportunity_created_date', 'contract_signed_date',
            'audit_scheduled_date', 'audit_completed_date', 'certificate_issued_date',
            'next_milestone', 'next_milestone_date', 'owner', 'owner_id', 'created_by',
            'created_at', 'updated_at', 'audits_count', 'milestones_count', 'overdue_milestones_count'
        ]
        read_only_fields = ['pipeline_id', 'created_by', 'created_at', 'updated_at']
    
    def get_audits_count(self, obj):
        return obj.audits.count()
    
    def get_milestones_count(self, obj):
        return obj.milestones.count()
    
    def get_overdue_milestones_count(self, obj):
        from django.utils import timezone
        return obj.milestones.filter(
            is_completed=False,
            due_date__lt=timezone.now().date()
        ).count()
    



class JobPipelineDetailSerializer(JobPipelineSerializer):
    """Detailed job pipeline serializer with related objects"""
    lead = LeadBasicSerializer(read_only=True)
    opportunity = OpportunityBasicSerializer(read_only=True)
    contract = ContractBasicSerializer(read_only=True)
    audits = AuditBasicSerializer(many=True, read_only=True)
    milestones = PipelineMilestoneSerializer(many=True, read_only=True)
    recent_transitions = serializers.SerializerMethodField()
    
    # Formatted references
    opportunity_ref = serializers.CharField(read_only=True)
    contract_ref = serializers.CharField(read_only=True)
    audit_refs = serializers.SerializerMethodField()
    
    class Meta(JobPipelineSerializer.Meta):
        fields = JobPipelineSerializer.Meta.fields + [
            'lead', 'opportunity', 'contract', 'audits', 'milestones', 'recent_transitions',
            'opportunity_ref', 'contract_ref', 'audit_refs'
        ]
    
    def get_recent_transitions(self, obj):
        """Get last 5 stage transitions"""
        recent = obj.stage_transitions.select_related('transitioned_by')[:5]
        return PipelineStageTransitionSerializer(recent, many=True).data

    def get_audit_refs(self, obj):
        """Get formatted references for all audits"""
        return [obj.get_audit_ref(audit) for audit in obj.audits.all()]


class JobPipelineStatsSerializer(serializers.Serializer):
    """Serializer for pipeline statistics"""
    total_pipelines = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    stage_distribution = serializers.ListField(child=serializers.DictField())
    status_distribution = serializers.ListField(child=serializers.DictField())
    average_stage_time = serializers.FloatField()
    monthly_trend = serializers.ListField(child=serializers.DictField())
    top_owners = serializers.ListField(child=serializers.DictField())


class PipelineCreateFromLeadSerializer(serializers.Serializer):
    """Serializer for creating pipeline from lead"""
    lead_id = serializers.IntegerField()
    owner_id = serializers.IntegerField(required=False, allow_null=True)
    service_description = serializers.CharField(required=False)
    
    def create(self, validated_data):
        lead = Lead.objects.get(id=validated_data['lead_id'])
        
        # Create pipeline
        pipeline = JobPipeline.objects.create(
            client_name=lead.company_name,
            service_description=validated_data.get('service_description', f"Services for {lead.company_name}"),
            estimated_value=lead.estimated_value,
            currency=lead.currency,
            current_stage='LEAD',
            lead=lead,
            owner_id=validated_data.get('owner_id'),
            created_by=self.context['request'].user,
            lead_created_date=lead.created_at
        )
        
        return pipeline


class PipelineCreateFromOpportunitySerializer(serializers.Serializer):
    """Serializer for creating pipeline from opportunity"""
    opportunity_id = serializers.IntegerField()
    owner_id = serializers.IntegerField(required=False, allow_null=True)
    
    def create(self, validated_data):
        opportunity = Opportunity.objects.get(id=validated_data['opportunity_id'])
        
        # Create pipeline
        pipeline = JobPipeline.objects.create(
            client_name=opportunity.client.name if opportunity.client else "Unknown Client",
            service_description=opportunity.description,
            estimated_value=opportunity.estimated_value,
            currency=opportunity.currency,
            current_stage='OPPORTUNITY',
            opportunity=opportunity,
            owner=opportunity.owner,
            created_by=self.context['request'].user,
            opportunity_created_date=opportunity.created_at
        )
        
        return pipeline