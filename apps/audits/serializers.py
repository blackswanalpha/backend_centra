from rest_framework import serializers
from .models import (
    Audit, AuditFinding, ISOStandard, AuditChecklist, ChecklistItem,
    ChecklistSection, AuditChecklistResponse, ChecklistEvidence, AuditDocument
)
from apps.clients.serializers import ClientSerializer
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (minimal)."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
        read_only_fields = ['id', 'username', 'email']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class ISOStandardSerializer(serializers.ModelSerializer):
    """Serializer for ISO Standard."""
    default_template_title = serializers.CharField(source='default_template.title', read_only=True)

    class Meta:
        model = ISOStandard
        fields = ['id', 'code', 'name', 'description', 'is_active', 'default_template', 'default_template_title', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class AuditFindingSerializer(serializers.ModelSerializer):
    """Serializer for Audit Findings."""
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditFinding
        fields = [
            'id', 'audit', 'finding_number', 'finding_type', 'clause_reference',
            'description', 'evidence', 'requirement', 'correction', 'corrective_action',
            'root_cause', 'target_date', 'actual_closure_date', 'status',
            'responsible_person', 'verified_by', 'verified_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return f"{obj.verified_by.first_name} {obj.verified_by.last_name}".strip() or obj.verified_by.username
        return None


class AuditDocumentSerializer(serializers.ModelSerializer):
    """Serializer for Audit Documents."""
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = AuditDocument
        fields = [
            'id', 'audit', 'file', 'file_url', 'filename', 'original_name',
            'description', 'category', 'file_size', 'uploaded_by',
            'uploaded_by_name', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_at', 'file_size', 'filename']

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}".strip() or obj.uploaded_by.username
        return None

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class AuditSerializer(serializers.ModelSerializer):
    """Serializer for Audit model."""
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_data = ClientSerializer(source='client', read_only=True)
    iso_standard_name = serializers.CharField(source='iso_standard.code', read_only=True)
    iso_standard_data = ISOStandardSerializer(source='iso_standard', read_only=True)
    lead_auditor_name = serializers.SerializerMethodField()
    lead_auditor_data = UserSerializer(source='lead_auditor', read_only=True)
    auditors_data = UserSerializer(source='auditors', many=True, read_only=True)
    findings = AuditFindingSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    audit_template_data = serializers.SerializerMethodField()
    audit_templates_data = serializers.SerializerMethodField()
    checklist_responses = serializers.SerializerMethodField()

    # Frontend-compatible field names
    startDate = serializers.DateField(source='planned_start_date', required=False)
    endDate = serializers.DateField(source='planned_end_date', required=False)
    
    class Meta:
        model = Audit
        fields = [
            'id', 'client', 'client_name', 'client_data', 'iso_standard',
            'iso_standard_name', 'iso_standard_data', 'audit_type', 'audit_number',
            'title', 'description', 'scope', 'planned_start_date', 'planned_end_date',
            'actual_start_date', 'actual_end_date', 'lead_auditor', 'lead_auditor_name',
            'lead_auditor_data', 'auditors', 'auditors_data', 'status',
            'audit_template', 'audit_template_data', 'audit_templates', 'audit_templates_data',
            'checklist_responses', 'findings_count', 'major_findings', 'minor_findings', 'opportunities',
            'certificate_number', 'certificate_issue_date', 'certificate_expiry_date',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'findings', 'startDate', 'endDate'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'audit_number']
    
    def get_lead_auditor_name(self, obj):
        if obj.lead_auditor:
            return f"{obj.lead_auditor.first_name} {obj.lead_auditor.last_name}".strip() or obj.lead_auditor.username
        return None
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
    
    def get_audit_template_data(self, obj):
        if obj.audit_template:
            # Avoid circular import by getting the serializer class at runtime
            return {
                'id': obj.audit_template.id,
                'title': obj.audit_template.title,
                'description': obj.audit_template.description,
                'company_name': obj.audit_template.company_name,
                'primary_color': obj.audit_template.primary_color,
                'logo_url': obj.audit_template.logo.url if obj.audit_template.logo else None,
                'items_count': obj.audit_template.items.count(),
                'iso_standard_name': obj.audit_template.iso_standard.code
            }
        return None

    def get_audit_templates_data(self, obj):
        """Serialize all associated templates for multi-template audits"""
        templates = obj.audit_templates.all()
        return [
            {
                'id': template.id,
                'title': template.title,
                'description': template.description,
                'company_name': template.company_name,
                'primary_color': template.primary_color,
                'logo_url': template.logo.url if template.logo else None,
                'items_count': template.items.count(),
                'iso_standard_id': template.iso_standard.id,
                'iso_standard_name': template.iso_standard.code
            }
            for template in templates
        ]

    def get_checklist_responses(self, obj):
        responses = obj.checklist_responses.all()
        return AuditChecklistResponseSerializer(responses, many=True).data
    
    def create(self, validated_data):
        # Auto-generate audit number if not provided
        if not validated_data.get('audit_number'):
            # Generate audit number: A-YYYY-XXX
            from django.utils import timezone
            year = timezone.now().year
            last_audit = Audit.objects.filter(
                audit_number__startswith=f'A-{year}-'
            ).order_by('-audit_number').first()
            
            if last_audit:
                last_number = int(last_audit.audit_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            validated_data['audit_number'] = f'A-{year}-{new_number:03d}'
        
        return super().create(validated_data)


class ChecklistSectionSerializer(serializers.ModelSerializer):
    """Serializer for Checklist Sections."""
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChecklistSection
        fields = ['id', 'checklist', 'name', 'description', 'order', 'items_count']
        
    def get_items_count(self, obj):
        return obj.items.count()


class ChecklistItemSerializer(serializers.ModelSerializer):
    """Serializer for Checklist Items."""
    section_data = ChecklistSectionSerializer(source='section', read_only=True)
    
    class Meta:
        model = ChecklistItem
        fields = [
            'id', 'checklist', 'section', 'section_data', 'clause_reference', 
            'iso_clause', 'item_type', 'question', 'guidance', 'actions_required',
            'allow_comments', 'allow_notes', 'allow_evidence_upload', 
            'section_name', 'subsection', 'is_mandatory', 'order'
        ]


class ChecklistEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for Checklist Evidence."""
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ChecklistEvidence
        fields = [
            'id', 'file', 'file_url', 'filename', 'original_name', 'description',
            'file_size', 'uploaded_by', 'uploaded_by_name', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_at']
        
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}".strip() or obj.uploaded_by.username
        return None
        
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class AuditChecklistResponseSerializer(serializers.ModelSerializer):
    """Serializer for Audit Checklist Responses."""
    checklist_item = ChecklistItemSerializer(read_only=True)
    checklist_item_id = serializers.PrimaryKeyRelatedField(
        queryset=ChecklistItem.objects.all(),
        source='checklist_item',
        write_only=True
    )
    evidence_files = ChecklistEvidenceSerializer(many=True, read_only=True)
    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditChecklistResponse
        fields = [
            'id', 'audit', 'checklist_item', 'checklist_item_id', 'compliance_status', 'auditor_comments',
            'auditor_notes', 'actions_taken', 'evidence_description', 'corrective_action_required',
            'completed_by', 'completed_by_name', 'completed_at', 'evidence_files',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_completed_by_name(self, obj):
        if obj.completed_by:
            return f"{obj.completed_by.first_name} {obj.completed_by.last_name}".strip() or obj.completed_by.username
        return None


class AuditChecklistSerializer(serializers.ModelSerializer):
    """Serializer for Audit Checklists."""
    iso_standard_data = ISOStandardSerializer(source='iso_standard', read_only=True)
    items = ChecklistItemSerializer(many=True, required=False)
    sections = ChecklistSectionSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditChecklist
        fields = [
            'id', 'iso_standard', 'iso_standard_data', 'title', 'description',
            'is_template', 'logo', 'logo_url', 'company_name', 'header_content', 
            'footer_content', 'primary_color', 'include_compliance_checkboxes',
            'enable_comments', 'enable_notes', 'enable_actions',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 
            'items', 'sections'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None
        
    def get_logo_url(self, obj):
        if obj.logo:
            return obj.logo.url
        return None

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        checklist = AuditChecklist.objects.create(**validated_data)

        # Create checklist items
        for item_data in items_data:
            ChecklistItem.objects.create(checklist=checklist, **item_data)

        return checklist

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        # Update checklist fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update items if provided
        if items_data is not None:
            # Delete existing items
            instance.items.all().delete()
            # Create new items
            for item_data in items_data:
                ChecklistItem.objects.create(checklist=instance, **item_data)

        return instance

