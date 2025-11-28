from rest_framework import serializers
from django.contrib.auth.models import User
from apps.business_development.models import Lead, Opportunity, Proposal, Contract, Activity
from apps.clients.serializers import ClientSerializer


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for nested representations"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
        read_only_fields = ['id', 'username', 'email']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class LeadSerializer(serializers.ModelSerializer):
    """Serializer for Lead model"""
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'company_name', 'contact_person', 'email', 'phone', 'position',
            'source', 'industry', 'estimated_value', 'currency', 'status', 'probability',
            'assigned_to', 'assigned_to_name', 'first_contact_date', 'last_contact_date',
            'expected_close_date', 'converted_to_client', 'conversion_date', 'notes',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class OpportunityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for opportunity lists"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Opportunity
        fields = [
            'id', 'title', 'client', 'client_name', 'service_type', 'estimated_value',
            'currency', 'probability', 'status', 'expected_close_date', 'owner', 'owner_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_owner_name(self, obj):
        if obj.owner:
            return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.username
        return None


class OpportunitySerializer(serializers.ModelSerializer):
    """Full serializer for Opportunity model with nested data"""
    client = ClientSerializer(read_only=True)
    client_id = serializers.IntegerField(write_only=True)
    owner = UserSerializer(read_only=True)
    owner_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    created_by = UserSerializer(read_only=True)
    last_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = Opportunity
        fields = [
            'id', 'client', 'client_id', 'lead', 'title', 'description', 'service_type',
            'estimated_value', 'currency', 'probability', 'status', 'expected_close_date',
            'actual_close_date', 'owner', 'owner_id', 'competitors', 'decision_criteria',
            'decision_makers', 'created_by', 'created_at', 'updated_at', 'last_activity'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_last_activity(self, obj):
        """Get the most recent activity for this opportunity"""
        try:
            activity = obj.activities.order_by('-activity_date').first()
            if activity:
                return {
                    'type': activity.activity_type,
                    'date': activity.activity_date,
                    'description': activity.description[:100] if activity.description else None
                }
        except:
            pass
        return None


class ProposalSerializer(serializers.ModelSerializer):
    """Serializer for Proposal model"""
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    prepared_by_name = serializers.CharField(source='prepared_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Proposal
        fields = [
            'id', 'opportunity', 'opportunity_title', 'proposal_number', 'title',
            'executive_summary', 'scope_of_work', 'methodology', 'timeline', 'deliverables',
            'total_value', 'currency', 'payment_terms', 'status', 'prepared_by', 'prepared_by_name',
            'approved_by', 'approved_by_name', 'sent_date', 'response_deadline', 'response_date',
            'document_file', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'proposal_number', 'created_at', 'updated_at']


class ContractSerializer(serializers.ModelSerializer):
    """Serializer for Contract model"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    proposal_number = serializers.CharField(source='proposal.proposal_number', read_only=True)
    
    class Meta:
        model = Contract
        fields = [
            'id', 'proposal', 'proposal_number', 'client', 'client_name', 'contract_number',
            'contract_type', 'title', 'description', 'contract_value', 'currency', 'payment_terms',
            'status', 'start_date', 'end_date', 'renewal_date', 'auto_renew', 'signed_by_client',
            'signed_by_company', 'client_signature_date', 'company_signature_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'contract_number', 'created_at', 'updated_at']


class ActivitySerializer(serializers.ModelSerializer):
    """Serializer for Activity model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Activity
        fields = [
            'id', 'opportunity', 'activity_type', 'activity_date', 'description',
            'outcome', 'next_steps', 'follow_up_date', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

