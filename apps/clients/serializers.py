from rest_framework import serializers
from .models import Client, ClientContact, IntakeLink, IntakeSubmission


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for Client model that matches frontend interface.
    Handles field name transformations between frontend (camelCase) and backend (snake_case).
    """

    # Map frontend camelCase to backend snake_case
    siteContact = serializers.CharField(source='site_contact', required=False, allow_blank=True, allow_null=True)
    sitePhone = serializers.CharField(source='site_phone', required=False, allow_blank=True, allow_null=True)
    healthScore = serializers.IntegerField(source='health_score', required=False, default=100)
    lastAuditDate = serializers.DateField(source='last_audit_date', required=False, allow_null=True)
    nextAuditDate = serializers.DateField(source='next_audit_date', required=False, allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)

    # Billing fields (camelCase mapping)
    currencyCode = serializers.CharField(source='currency_code', required=False, allow_blank=True, allow_null=True)
    billingAttention = serializers.CharField(source='billing_attention', required=False, allow_blank=True, allow_null=True)
    billingAddress = serializers.CharField(source='billing_address', required=False, allow_blank=True, allow_null=True)
    billingStreet2 = serializers.CharField(source='billing_street2', required=False, allow_blank=True, allow_null=True)
    billingCity = serializers.CharField(source='billing_city', required=False, allow_blank=True, allow_null=True)
    billingState = serializers.CharField(source='billing_state', required=False, allow_blank=True, allow_null=True)
    billingCountry = serializers.CharField(source='billing_country', required=False, allow_blank=True, allow_null=True)
    paymentTerms = serializers.CharField(source='payment_terms', required=False, allow_blank=True, allow_null=True)

    # Physical location fields (camelCase mapping)
    physicalAddress = serializers.CharField(source='physical_address', required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Project/Certification fields (camelCase mapping)
    projectRef = serializers.CharField(source='project_ref', required=False, allow_blank=True, allow_null=True)
    scopeOfCertification = serializers.CharField(source='scope_of_certification', required=False, allow_blank=True, allow_null=True)
    certificateNo = serializers.CharField(source='certificate_no', required=False, allow_blank=True, allow_null=True)
    registrationDate = serializers.DateField(source='registration_date', required=False, allow_null=True)
    certificateDate = serializers.DateField(source='certificate_date', required=False, allow_null=True)
    expiryDate = serializers.DateField(source='expiry_date', required=False, allow_null=True)

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'contact', 'email', 'phone', 'address',
            'siteContact', 'sitePhone', 'status', 'industry',
            'certifications', 'healthScore', 'lastAuditDate', 'nextAuditDate',
            'createdAt', 'updatedAt',
            # Billing fields
            'currencyCode', 'billingAttention', 'billingAddress', 'billingStreet2',
            'billingCity', 'billingState', 'billingCountry', 'paymentTerms',
            # Physical location fields
            'physicalAddress', 'city', 'country',
            # Project/Certification fields
            'projectRef', 'scopeOfCertification', 'certificateNo',
            'registrationDate', 'certificateDate', 'expiryDate'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'createdAt', 'updatedAt')

    def validate_certifications(self, value):
        """Ensure certifications is a list"""
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Certifications must be a list")
        return value

    def validate_health_score(self, value):
        """Validate health score is between 0 and 100"""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Health score must be between 0 and 100")
        return value


class ClientContactSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = ClientContact
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class IntakeLinkSerializer(serializers.ModelSerializer):
    submissions_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    is_exhausted = serializers.BooleanField(read_only=True)
    is_usable = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)

    class Meta:
        model = IntakeLink
        fields = [
            'id', 'title', 'token', 'access_code', 'description',
            'is_active', 'expires_at', 'max_uses', 'current_uses',
            'related_audit_id', 'related_project_id', 'notes', 'metadata',
            'last_accessed_at', 'created_by', 'created_by_name', 'created_at', 'updated_at',
            'submissions_count', 'is_expired', 'is_exhausted', 'is_usable',
            'status', 'status_display'
        ]
        read_only_fields = ('token', 'access_code', 'created_by', 'created_at', 'updated_at', 'current_uses', 'last_accessed_at')

    def get_submissions_count(self, obj):
        return obj.submissions.count()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username
        return None


class IntakeSubmissionSerializer(serializers.ModelSerializer):
    intake_title = serializers.CharField(source='intake_link.title', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = IntakeSubmission
        fields = [
            'id', 'intake_link', 'intake_title', 'client', 'client_data',
            'submitted_at', 'ip_address', 'user_agent',
            'status', 'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'notes', 'rejection_reason',
            'processed', 'processed_by', 'processed_at', 'company_name'
        ]
        read_only_fields = ('submitted_at', 'processed_by', 'processed_at', 'reviewed_by', 'reviewed_at')

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}".strip() or obj.reviewed_by.username
        return None

    def get_company_name(self, obj):
        return obj.client_data.get('name', 'Unknown') if obj.client_data else 'Unknown'