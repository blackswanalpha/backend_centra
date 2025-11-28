from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.crypto import get_random_string
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django.views.decorators.cache import cache_page
from .models import Client, ClientContact, IntakeLink, IntakeSubmission
from .serializers import ClientSerializer, ClientContactSerializer, IntakeLinkSerializer, IntakeSubmissionSerializer
import secrets
import string


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Client model with CRUD operations.
    Supports filtering, searching, and ordering.
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated access for testing
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'industry']
    search_fields = ['name', 'contact', 'email', 'industry']
    ordering_fields = ['name', 'created_at', 'status']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        # Save with created_by if user is authenticated
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        client = self.get_object()
        contacts = client.contacts.all()
        serializer = ClientContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def audits(self, request, pk=None):
        client = self.get_object()
        audits = client.audits.all()
        # Import here to avoid circular imports
        from apps.audits.serializers import AuditSerializer
        serializer = AuditSerializer(audits, many=True)
        return Response(serializer.data)


class ClientContactViewSet(viewsets.ModelViewSet):
    queryset = ClientContact.objects.all()
    serializer_class = ClientContactSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['client', 'is_primary']
    search_fields = ['name', 'email', 'position']


def generate_access_code():
    """Generate a secure 8-character access code (XXXX-XXXX format)"""
    # Use uppercase letters and digits, excluding similar-looking characters
    chars = ''.join(set(string.ascii_uppercase + string.digits) - set('0O1IL'))
    code = ''.join(secrets.choice(chars) for _ in range(8))
    return f"{code[:4]}-{code[4:]}"


def generate_link_token():
    """Generate a secure 64-character token for the intake link"""
    return secrets.token_urlsafe(48)[:64]


class IntakeLinkViewSet(viewsets.ModelViewSet):
    queryset = IntakeLink.objects.all()
    serializer_class = IntakeLinkSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated access for testing
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['title', 'description']

    def perform_create(self, serializer):
        # Generate unique token and access code
        token = generate_link_token()
        while IntakeLink.objects.filter(token=token).exists():
            token = generate_link_token()

        access_code = generate_access_code()
        while IntakeLink.objects.filter(access_code=access_code).exists():
            access_code = generate_access_code()

        # Set created_by if user is authenticated
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user, token=token, access_code=access_code)
        else:
            serializer.save(token=token, access_code=access_code)

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        intake_link = self.get_object()
        submissions = intake_link.submissions.all()
        serializer = IntakeSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)


class IntakeSubmissionViewSet(viewsets.ModelViewSet):
    queryset = IntakeSubmission.objects.all()
    serializer_class = IntakeSubmissionSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated access for testing
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['intake_link', 'processed', 'status']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']

    @action(detail=True, methods=['post'])
    def mark_processed(self, request, pk=None):
        submission = self.get_object()
        submission.processed = True
        submission.processed_by = request.user
        submission.save()
        return Response({'status': 'processed'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a submission and create a client record.
        POST /api/v1/intake-submissions/{id}/approve/
        Body: { "notes": "Optional review notes" }
        """
        from django.utils import timezone

        submission = self.get_object()

        # Check if already reviewed
        if submission.status != 'pending':
            return Response(
                {'error': f'This submission has already been {submission.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get notes from request
        notes = request.data.get('notes', '')

        # Create client from submission data
        client_data = submission.client_data
        try:
            # Build address from components
            address_parts = []
            if client_data.get('address'):
                address_parts.append(client_data.get('address'))
            if client_data.get('city'):
                address_parts.append(client_data.get('city'))
            if client_data.get('state'):
                address_parts.append(client_data.get('state'))
            if client_data.get('zipCode'):
                address_parts.append(client_data.get('zipCode'))
            if client_data.get('country'):
                address_parts.append(client_data.get('country'))

            full_address = ', '.join(address_parts) if address_parts else ''

            # Prepare certifications list
            certifications = []
            if client_data.get('certificationType'):
                certifications.append(client_data.get('certificationType'))

            client = Client.objects.create(
                name=client_data.get('name', ''),
                contact=client_data.get('contact', ''),
                email=client_data.get('email', ''),
                phone=client_data.get('phone', ''),
                address=full_address,
                industry=client_data.get('industry', ''),
                certifications=certifications,
                status='active',
                created_by=request.user if request.user.is_authenticated else None
            )

            # Update submission
            submission.status = 'approved'
            submission.client = client
            submission.reviewed_by = request.user if request.user.is_authenticated else None
            submission.reviewed_at = timezone.now()
            submission.notes = notes
            submission.processed = True
            submission.processed_by = request.user if request.user.is_authenticated else None
            submission.processed_at = timezone.now()
            submission.save()

            # Serialize the updated submission
            serializer = self.get_serializer(submission)

            return Response({
                'success': True,
                'message': 'Submission approved and client record created successfully',
                'submission': serializer.data,
                'client_id': client.id
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to create client: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a submission.
        POST /api/v1/intake-submissions/{id}/reject/
        Body: { "rejectionReason": "Required reason", "notes": "Optional review notes" }
        """
        from django.utils import timezone

        submission = self.get_object()

        # Check if already reviewed
        if submission.status != 'pending':
            return Response(
                {'error': f'This submission has already been {submission.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get rejection reason and notes
        rejection_reason = request.data.get('rejectionReason', '')
        notes = request.data.get('notes', '')

        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update submission
        submission.status = 'rejected'
        submission.reviewed_by = request.user if request.user.is_authenticated else None
        submission.reviewed_at = timezone.now()
        submission.notes = notes
        submission.rejection_reason = rejection_reason
        submission.processed = True
        submission.processed_by = request.user if request.user.is_authenticated else None
        submission.processed_at = timezone.now()
        submission.save()

        # Serialize the updated submission
        serializer = self.get_serializer(submission)

        return Response({
            'success': True,
            'message': 'Submission rejected successfully',
            'submission': serializer.data
        })


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/m', method='POST')  # 10 requests per minute per IP
def validate_intake_access_code(request):
    """
    Validate an access code for an intake link.
    POST /api/v1/clients/intake/validate/
    Body: { "linkToken": "...", "accessCode": "XXXX-XXXX" }

    Rate limit: 10 requests per minute per IP address
    """
    link_token = request.data.get('linkToken')
    access_code = request.data.get('accessCode')

    if not link_token or not access_code:
        return Response({
            'valid': False,
            'error': 'Missing linkToken or accessCode'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        intake_link = IntakeLink.objects.get(token=link_token)
    except IntakeLink.DoesNotExist:
        return Response({
            'valid': False,
            'error': 'Invalid link'
        }, status=status.HTTP_404_NOT_FOUND)

    # Validate access code
    if intake_link.access_code != access_code:
        return Response({
            'valid': False,
            'error': 'Invalid access code'
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Check if link is usable
    if not intake_link.is_active:
        return Response({
            'valid': False,
            'error': 'This link has been deactivated'
        }, status=status.HTTP_403_FORBIDDEN)

    if intake_link.is_expired:
        return Response({
            'valid': False,
            'error': 'This link has expired'
        }, status=status.HTTP_403_FORBIDDEN)

    if intake_link.is_exhausted:
        return Response({
            'valid': False,
            'error': 'This link has reached its maximum number of uses'
        }, status=status.HTTP_403_FORBIDDEN)

    # Update last accessed time
    intake_link.last_accessed_at = timezone.now()
    intake_link.save(update_fields=['last_accessed_at'])

    return Response({
        'valid': True,
        'linkData': {
            'id': intake_link.id,
            'title': intake_link.title,
            'description': intake_link.description,
            'maxUses': intake_link.max_uses,
            'currentUses': intake_link.current_uses,
            'expiresAt': intake_link.expires_at.isoformat()
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', method='POST')  # 5 submissions per minute per IP
def submit_intake_form(request, token):
    """
    Submit an intake form.
    POST /api/v1/clients/intake/{token}/submit/
    Body: { "accessCode": "XXXX-XXXX", "formData": {...} }

    Rate limit: 5 requests per minute per IP address
    """
    access_code = request.data.get('accessCode')
    form_data = request.data.get('formData')

    if not access_code or not form_data:
        return Response({
            'success': False,
            'error': 'Missing accessCode or formData'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        intake_link = IntakeLink.objects.get(token=token)
    except IntakeLink.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid link'
        }, status=status.HTTP_404_NOT_FOUND)

    # Validate access code
    if intake_link.access_code != access_code:
        return Response({
            'success': False,
            'error': 'Invalid access code'
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Check if link is usable
    if not intake_link.is_usable:
        return Response({
            'success': False,
            'error': 'This link is no longer available'
        }, status=status.HTTP_403_FORBIDDEN)

    # Get client IP and user agent
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # Create submission
    submission = IntakeSubmission.objects.create(
        intake_link=intake_link,
        client_data=form_data,
        ip_address=ip_address,
        user_agent=user_agent,
        status='pending'
    )

    # Increment usage count
    intake_link.current_uses += 1
    intake_link.last_accessed_at = timezone.now()
    intake_link.save(update_fields=['current_uses', 'last_accessed_at'])

    serializer = IntakeSubmissionSerializer(submission)

    return Response({
        'success': True,
        'submission': serializer.data
    }, status=status.HTTP_201_CREATED)