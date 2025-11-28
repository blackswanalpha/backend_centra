from rest_framework import serializers
from django.contrib.auth.models import User
from apps.business_development.models import Lead, Opportunity, Proposal, Contract, ActivityLog
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
    """Serializer for Contract model with comprehensive certification agreement fields"""
    # Read-only computed fields
    client_name = serializers.SerializerMethodField()
    proposal_number = serializers.CharField(source='proposal.proposal_number', read_only=True, allow_null=True)
    opportunity_title = serializers.CharField(source='opportunity.title', read_only=True)
    total_standards_count = serializers.IntegerField(read_only=True)
    total_year_1_fee = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_year_2_fee = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_year_3_fee = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    # Write-only fields for creation
    opportunity_id = serializers.IntegerField(write_only=True)
    
    # Expose client_id for frontend convenience
    client_id = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            # Core relationships
            'id', 'proposal', 'proposal_number', 'opportunity', 'opportunity_id', 'opportunity_title',
            'client_name', 'client_id', 'contract_number',
            
            # Contract details
            'contract_type', 'title', 'description', 'agreement_date',
            
            # Client contact information
            'client_organization', 'client_address', 'client_contact_person', 'client_telephone',
            'client_email', 'client_secondary_email', 'client_website', 'site_covered',
            
            # Certification body information
            'cb_name', 'cb_address', 'cb_role',
            
            # Scope of work
            'iso_standards', 'scope_of_work',
            
            # Certification process details
            'stage_1_audit_days', 'stage_1_audit_description', 'stage_1_remote_allowed',
            'stage_2_audit_days', 'stage_2_audit_description',
            'surveillance_audit_frequency', 'surveillance_audit_description',
            'recertification_audit_timing', 'recertification_audit_description',
            
            # Timeline & certification cycle
            'start_date', 'end_date', 'duration_months', 'certification_cycle_years',
            'stage_1_stage_2_max_gap_days', 'nc_closure_max_days', 'certificate_issue_days',
            'certificate_validity_years', 'certificate_validity_extension_allowed',
            
            # Fee structure
            'fee_per_standard_year_1', 'fee_per_standard_year_2', 'fee_per_standard_year_3',
            'recertification_fee_tbd', 'recertification_fee', 'additional_fees_description',
            
            # Total financial
            'contract_value', 'currency', 'payment_schedule',
            
            # Cancellation policy
            'cancellation_notice_days', 'cancellation_fee_applies',
            
            # Confidentiality & data protection
            'confidentiality_clause', 'data_protection_compliance',
            
            # Client responsibilities
            'client_responsibilities',
            
            # Status
            'status',
            
            # Signatures
            'signed_by_client_name', 'signed_by_client_position', 'client_signed_date',
            'signed_by_company', 'signed_by_company_name', 'signed_by_company_position', 'company_signed_date',
            
            # Files
            'contract_file',
            
            # Termination & renewal
            'termination_notice_days', 'termination_fee_waiver', 'auto_renewal', 'renewal_notice_days',
            
            # Legal
            'entire_agreement_clause',
            
            # Computed fields
            'total_standards_count', 'total_year_1_fee', 'total_year_2_fee', 'total_year_3_fee',
            
            # Audit trail
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'contract_number', 'created_at', 'updated_at']
    
    def get_client_id(self, obj):
        """Get client ID from the linked opportunity or by name"""
        if obj.opportunity and obj.opportunity.client:
            return obj.opportunity.client.id
        
        # Fallback: try to find client by organization name
        if obj.client_organization:
            from apps.clients.models import Client
            client = Client.objects.filter(name__iexact=obj.client_organization).first()
            if client:
                return client.id
        return None

    def get_client_name(self, obj):
        """Get client name from the linked opportunity"""
        if obj.opportunity and obj.opportunity.client:
            return obj.opportunity.client.name
        return obj.client_organization

    def create(self, validated_data):
        """Generate contract number automatically on creation"""
        from datetime import datetime

        # Generate contract number: CON-YYYY-NNNN
        year = datetime.now().year
        # Get the count of contracts created this year
        year_start = datetime(year, 1, 1)
        count = Contract.objects.filter(created_at__gte=year_start).count() + 1
        contract_number = f"CON-{year}-{count:04d}"

        # Ensure uniqueness
        while Contract.objects.filter(contract_number=contract_number).exists():
            count += 1
            contract_number = f"CON-{year}-{count:04d}"

        validated_data['contract_number'] = contract_number
        
        # Auto-populate client information from opportunity if not provided
        opportunity_id = validated_data.get('opportunity_id')
        if opportunity_id:
            try:
                opportunity = Opportunity.objects.select_related('client').get(id=opportunity_id)
                if opportunity.client and not validated_data.get('client_organization'):
                    validated_data['client_organization'] = opportunity.client.name
                    validated_data['client_address'] = getattr(opportunity.client, 'address', '')
                    validated_data['client_email'] = getattr(opportunity.client, 'email', '')
                    validated_data['client_telephone'] = getattr(opportunity.client, 'phone', '')
            except Opportunity.DoesNotExist:
                pass
        
        return super().create(validated_data)


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for ActivityLog model"""
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'lead', 'opportunity', 'client', 'client_name', 'activity_type', 'subject', 'description',
            'activity_date', 'duration_minutes', 'follow_up_required', 'follow_up_date',
            'performed_by', 'performed_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'performed_by']

