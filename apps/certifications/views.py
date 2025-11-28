from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from datetime import date, timedelta

from .models import Certification, CertificateTemplate, CertificationHistory
from .serializers import (
    CertificationListSerializer,
    CertificationDetailSerializer,
    CertificationCreateUpdateSerializer,
    CertificateTemplateSerializer,
    CertificationHistorySerializer
)
from .services import CertificateGenerationService


class CertificateTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing certificate templates.

    Endpoints:
    - GET /api/certificate-templates/ - List all templates
    - POST /api/certificate-templates/ - Create new template
    - GET /api/certificate-templates/{id}/ - Get template details
    - PUT /api/certificate-templates/{id}/ - Update template
    - DELETE /api/certificate-templates/{id}/ - Delete template
    """
    queryset = CertificateTemplate.objects.all()
    serializer_class = CertificateTemplateSerializer
    permission_classes = [AllowAny]  # Temporary for development
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['template_type', 'iso_standard', 'is_active', 'is_default']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active templates."""
        templates = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get default templates for each ISO standard."""
        templates = self.queryset.filter(is_default=True, is_active=True)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)


class CertificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing certifications.

    Endpoints:
    - GET /api/certifications/ - List all certifications
    - POST /api/certifications/ - Create new certification
    - GET /api/certifications/{id}/ - Get certification details
    - PUT /api/certifications/{id}/ - Update certification
    - DELETE /api/certifications/{id}/ - Delete certification
    - POST /api/certifications/{id}/generate/ - Generate certificate PDF
    - POST /api/certifications/{id}/renew/ - Renew certification
    - POST /api/certifications/{id}/suspend/ - Suspend certification
    - POST /api/certifications/{id}/revoke/ - Revoke certification
    """
    queryset = Certification.objects.select_related(
        'client', 'iso_standard', 'audit', 'lead_auditor', 'template', 'created_by'
    ).prefetch_related('history')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'iso_standard', 'client', 'lead_auditor']
    search_fields = ['certificate_number', 'client__name', 'scope', 'certification_body']
    ordering_fields = ['issue_date', 'expiry_date', 'created_at', 'certificate_number']
    ordering = ['-issue_date']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CertificationListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CertificationCreateUpdateSerializer
        else:
            return CertificationDetailSerializer

    def perform_create(self, serializer):
        """Create certification and log history."""
        certification = serializer.save(created_by=self.request.user)

        # Create history entry
        CertificationHistory.objects.create(
            certification=certification,
            action='created',
            new_status=certification.status,
            performed_by=self.request.user,
            notes=f"Certification created"
        )

    def perform_update(self, serializer):
        """Update certification and log history."""
        old_status = serializer.instance.status
        certification = serializer.save()

        # Create history entry if status changed
        if old_status != certification.status:
            CertificationHistory.objects.create(
                certification=certification,
                action='updated',
                previous_status=old_status,
                new_status=certification.status,
                performed_by=self.request.user,
                notes=f"Status changed from {old_status} to {certification.status}"
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get certification statistics."""
        total = self.queryset.count()
        active = self.queryset.filter(status='active').count()
        expiring_soon = self.queryset.filter(status='expiring-soon').count()
        expired = self.queryset.filter(status='expired').count()
        suspended = self.queryset.filter(status='suspended').count()
        revoked = self.queryset.filter(status='revoked').count()
        pending = self.queryset.filter(status='pending').count()

        return Response({
            'total': total,
            'active': active,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'suspended': suspended,
            'revoked': revoked,
            'pending': pending
        })

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get certifications expiring within specified days (default 90)."""
        days = int(request.query_params.get('days', 90))
        expiry_threshold = date.today() + timedelta(days=days)

        certifications = self.queryset.filter(
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=date.today(),
            status__in=['active', 'expiring-soon']
        )

        serializer = self.get_serializer(certifications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """
        Generate certificate document from template.
        """
        certification = self.get_object()

        if not certification.template:
            return Response(
                {'error': 'No template assigned to this certification'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Generate certificate using service
            service = CertificateGenerationService(certification)
            output_path = service.generate(user=request.user)

            # Create history entry
            CertificationHistory.objects.create(
                certification=certification,
                action='document_generated',
                performed_by=request.user,
                notes=f'Certificate document generated: {output_path}'
            )

            # Refresh certification to get updated document_url
            certification.refresh_from_db()
            serializer = self.get_serializer(certification)

            return Response({
                'message': 'Certificate generated successfully',
                'certification': serializer.data,
                'document_url': certification.document_url.url if certification.document_url else None
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to generate certificate: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """Renew a certification."""
        certification = self.get_object()

        # Get new expiry date from request
        new_expiry_date = request.data.get('expiry_date')
        if not new_expiry_date:
            return Response(
                {'error': 'New expiry date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_expiry = certification.expiry_date
        old_status = certification.status

        # Update certification
        certification.expiry_date = new_expiry_date
        certification.status = 'active'
        certification.save()

        # Create history entry
        CertificationHistory.objects.create(
            certification=certification,
            action='renewed',
            previous_status=old_status,
            new_status='active',
            performed_by=request.user,
            notes=f'Certification renewed. Expiry date changed from {old_expiry} to {new_expiry_date}',
            metadata={'old_expiry_date': str(old_expiry), 'new_expiry_date': str(new_expiry_date)}
        )

        serializer = self.get_serializer(certification)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a certification."""
        certification = self.get_object()

        if certification.status == 'suspended':
            return Response(
                {'error': 'Certification is already suspended'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        old_status = certification.status

        # Update status
        certification.status = 'suspended'
        certification.save()

        # Create history entry
        CertificationHistory.objects.create(
            certification=certification,
            action='suspended',
            previous_status=old_status,
            new_status='suspended',
            performed_by=request.user,
            notes=f'Certification suspended. Reason: {reason}',
            metadata={'reason': reason}
        )

        serializer = self.get_serializer(certification)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a certification."""
        certification = self.get_object()

        if certification.status == 'revoked':
            return Response(
                {'error': 'Certification is already revoked'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        old_status = certification.status

        # Update status
        certification.status = 'revoked'
        certification.save()

        # Create history entry
        CertificationHistory.objects.create(
            certification=certification,
            action='revoked',
            previous_status=old_status,
            new_status='revoked',
            performed_by=request.user,
            notes=f'Certification revoked. Reason: {reason}',
            metadata={'reason': reason}
        )

        serializer = self.get_serializer(certification)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Reactivate a suspended certification."""
        certification = self.get_object()

        if certification.status not in ['suspended', 'revoked']:
            return Response(
                {'error': 'Only suspended or revoked certifications can be reactivated'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = certification.status

        # Update status
        certification.status = 'active'
        certification.save()

        # Create history entry
        CertificationHistory.objects.create(
            certification=certification,
            action='reactivated',
            previous_status=old_status,
            new_status='active',
            performed_by=request.user,
            notes='Certification reactivated'
        )

        serializer = self.get_serializer(certification)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_certification_search(request):
    """
    Public endpoint for searching certifications.
    No authentication required - for public ISO certification directory.

    Query parameters:
    - search: Search in certificate number, client name, scope, certification body
    - iso_standard__code: Filter by ISO standard code (e.g., ISO 9001)
    - status: Filter by status (active, pending, expired, etc.)
    - client__name: Filter by client name
    """
    # Only show active certifications in public search
    queryset = Certification.objects.filter(
        status='active'
    ).select_related(
        'client', 'iso_standard', 'lead_auditor'
    )

    # Apply search filter
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(certificate_number__icontains=search) |
            Q(client__name__icontains=search) |
            Q(scope__icontains=search) |
            Q(certification_body__icontains=search)
        )

    # Apply ISO standard filter
    iso_standard_code = request.query_params.get('iso_standard__code')
    if iso_standard_code:
        queryset = queryset.filter(iso_standard__code__icontains=iso_standard_code)

    # Apply status filter (though we default to active only)
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Apply client name filter
    client_name = request.query_params.get('client__name')
    if client_name:
        queryset = queryset.filter(client__name__icontains=client_name)

    # Order by issue date (newest first)
    queryset = queryset.order_by('-issue_date')

    # Paginate results
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    paginator.page_size = 50  # Show more results for public search
    page = paginator.paginate_queryset(queryset, request)

    # Serialize
    serializer = CertificationListSerializer(page, many=True)

    return paginator.get_paginated_response(serializer.data)
