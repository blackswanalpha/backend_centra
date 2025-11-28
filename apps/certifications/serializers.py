from rest_framework import serializers
from .models import Certification, CertificateTemplate, CertificationHistory
from apps.clients.models import Client
from apps.audits.models import ISOStandard, Audit
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (minimal)."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class ISOStandardSerializer(serializers.ModelSerializer):
    """Serializer for ISO Standard."""
    class Meta:
        model = ISOStandard
        fields = ['id', 'code', 'name', 'description']


class ClientMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for Client."""
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'industry']


class AuditMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for Audit."""
    class Meta:
        model = Audit
        fields = ['id', 'audit_number', 'title', 'audit_type', 'status']


class CertificateTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Certificate Templates."""
    iso_standard = ISOStandardSerializer(read_only=True)
    iso_standard_id = serializers.PrimaryKeyRelatedField(
        queryset=ISOStandard.objects.all(),
        source='iso_standard',
        write_only=True,
        required=False,
        allow_null=True
    )
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = CertificateTemplate
        fields = [
            'id', 'name', 'description', 'iso_standard', 'iso_standard_id',
            'template_type', 'template_file', 'variables', 'is_active',
            'is_default', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class CertificationHistorySerializer(serializers.ModelSerializer):
    """Serializer for Certification History."""
    performed_by = UserSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = CertificationHistory
        fields = [
            'id', 'action', 'action_display', 'previous_status', 'new_status',
            'notes', 'metadata', 'performed_by', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'performed_by']


class CertificationListSerializer(serializers.ModelSerializer):
    """Serializer for listing certifications (minimal data)."""
    client = ClientMinimalSerializer(read_only=True)
    iso_standard = ISOStandardSerializer(read_only=True)
    lead_auditor = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Certification
        fields = [
            'id', 'certificate_number', 'client', 'iso_standard', 'status',
            'status_display', 'issue_date', 'expiry_date', 'lead_auditor',
            'certification_body', 'days_until_expiry', 'is_expired', 'is_expiring_soon',
            'created_at', 'updated_at'
        ]


class CertificationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for certifications."""
    client = ClientMinimalSerializer(read_only=True)
    iso_standard = ISOStandardSerializer(read_only=True)
    audit = AuditMinimalSerializer(read_only=True)
    lead_auditor = UserSerializer(read_only=True)
    template = CertificateTemplateSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    history = CertificationHistorySerializer(many=True, read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Certification
        fields = [
            'id', 'certificate_number', 'client', 'iso_standard', 'audit',
            'issue_date', 'expiry_date', 'status', 'status_display', 'scope',
            'lead_auditor', 'certification_body', 'accreditation_number',
            'template', 'document_url', 'metadata', 'notes', 'created_by',
            'created_at', 'updated_at', 'days_until_expiry', 'is_expired',
            'is_expiring_soon', 'history'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class CertificationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating certifications."""
    
    class Meta:
        model = Certification
        fields = [
            'id', 'certificate_number', 'client', 'iso_standard', 'audit',
            'issue_date', 'expiry_date', 'status', 'scope', 'lead_auditor',
            'certification_body', 'accreditation_number', 'template',
            'document_url', 'metadata', 'notes'
        ]
        read_only_fields = ['id']
    
    def validate_certificate_number(self, value):
        """Ensure certificate number is unique."""
        instance = self.instance
        if instance is None:  # Creating new
            if Certification.objects.filter(certificate_number=value).exists():
                raise serializers.ValidationError("Certificate number already exists.")
        else:  # Updating existing
            if Certification.objects.filter(certificate_number=value).exclude(id=instance.id).exists():
                raise serializers.ValidationError("Certificate number already exists.")
        return value
    
    def validate(self, data):
        """Validate expiry date is after issue date."""
        issue_date = data.get('issue_date')
        expiry_date = data.get('expiry_date')
        
        if issue_date and expiry_date and expiry_date <= issue_date:
            raise serializers.ValidationError({
                'expiry_date': 'Expiry date must be after issue date.'
            })
        
        return data

