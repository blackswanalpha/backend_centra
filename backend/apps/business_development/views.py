from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q, Avg
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from apps.business_development.models import Lead, Opportunity, Proposal, Contract, Activity
from .serializers import (
    LeadSerializer, OpportunitySerializer, OpportunityListSerializer,
    ProposalSerializer, ContractSerializer, ActivitySerializer
)


class LeadViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lead model with CRUD operations.
    Supports filtering, searching, and ordering.
    """
    queryset = Lead.objects.select_related('assigned_to', 'created_by', 'converted_to_client').all()
    serializer_class = LeadSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'source', 'industry', 'assigned_to']
    search_fields = ['company_name', 'contact_person', 'email', 'industry']
    ordering_fields = ['company_name', 'created_at', 'expected_close_date', 'estimated_value']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """Convert a lead to an opportunity"""
        lead = self.get_object()

        # Check if already converted
        if lead.status == 'CONVERTED':
            return Response(
                {'error': 'Lead has already been converted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create opportunity from lead data
        opportunity_data = {
            'client_id': request.data.get('client_id'),
            'lead': lead,
            'title': request.data.get('title', f"{lead.company_name} - {lead.industry}"),
            'description': request.data.get('description', lead.notes),
            'service_type': request.data.get('service_type'),
            'estimated_value': lead.estimated_value or 0,
            'currency': lead.currency,
            'probability': lead.probability,
            'status': 'PROSPECTING',
            'expected_close_date': lead.expected_close_date or timezone.now().date() + timedelta(days=30),
            'owner_id': lead.assigned_to.id if lead.assigned_to else None,
            'created_by': request.user if request.user.is_authenticated else None
        }

        opportunity = Opportunity.objects.create(**opportunity_data)

        # Update lead status
        lead.status = 'CONVERTED'
        lead.conversion_date = timezone.now().date()
        lead.save()

        return Response(
            OpportunitySerializer(opportunity).data,
            status=status.HTTP_201_CREATED
        )


class OpportunityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Opportunity model with CRUD operations.
    Supports filtering, searching, ordering, and custom analytics.
    """
    queryset = Opportunity.objects.select_related('client', 'owner', 'created_by', 'lead').prefetch_related('activities').all()
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'service_type', 'owner', 'client']
    search_fields = ['title', 'description', 'client__name']
    ordering_fields = ['title', 'estimated_value', 'expected_close_date', 'probability', 'created_at']
    ordering = ['-expected_close_date']

    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return OpportunityListSerializer
        return OpportunitySerializer

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get pipeline statistics and analytics"""
        opportunities = self.filter_queryset(self.get_queryset())

        # Calculate total pipeline value
        total_pipeline = opportunities.aggregate(total=Sum('estimated_value'))['total'] or 0

        # Calculate weighted forecast (value * probability)
        weighted_forecast = sum(
            float(opp.estimated_value) * (opp.probability / 100)
            for opp in opportunities
        )

        # Won this month
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        won_this_month = opportunities.filter(
            status='CLOSED_WON',
            actual_close_date__gte=current_month_start
        ).aggregate(total=Sum('estimated_value'))['total'] or 0

        # Conversion rate (closed won / total closed)
        total_closed = opportunities.filter(status__in=['CLOSED_WON', 'CLOSED_LOST']).count()
        closed_won = opportunities.filter(status='CLOSED_WON').count()
        conversion_rate = (closed_won / total_closed * 100) if total_closed > 0 else 0

        # Average deal size
        avg_deal_size = opportunities.aggregate(avg=Avg('estimated_value'))['avg'] or 0

        # By stage breakdown
        by_stage = {}
        for stage_code, stage_name in Opportunity.STATUS_CHOICES:
            stage_opps = opportunities.filter(status=stage_code)
            by_stage[stage_code] = {
                'name': stage_name,
                'count': stage_opps.count(),
                'value': float(stage_opps.aggregate(Sum('estimated_value'))['estimated_value__sum'] or 0)
            }

        return Response({
            'success': True,
            'data': {
                'total_pipeline': float(total_pipeline),
                'opportunity_count': opportunities.count(),
                'weighted_forecast': float(weighted_forecast),
                'won_this_month': float(won_this_month),
                'conversion_rate': round(conversion_rate, 1),
                'average_deal_size': float(avg_deal_size),
                'by_stage': by_stage
            }
        })

    @action(detail=False, methods=['get'])
    def by_owner(self, request):
        """Get opportunities grouped by owner with performance metrics"""
        opportunities = self.filter_queryset(self.get_queryset())

        # Get all owners who have opportunities
        owners = User.objects.filter(
            opportunities_owned__isnull=False
        ).distinct()

        data = []
        for owner in owners:
            owner_opps = opportunities.filter(owner=owner)
            total_value = owner_opps.aggregate(Sum('estimated_value'))['estimated_value__sum'] or 0

            # Calculate weighted value
            weighted_value = sum(
                float(opp.estimated_value) * (opp.probability / 100)
                for opp in owner_opps
            )

            # Calculate win rate
            total_closed = owner_opps.filter(status__in=['CLOSED_WON', 'CLOSED_LOST']).count()
            closed_won = owner_opps.filter(status='CLOSED_WON').count()
            win_rate = (closed_won / total_closed * 100) if total_closed > 0 else 0

            data.append({
                'owner': {
                    'id': owner.id,
                    'name': f"{owner.first_name} {owner.last_name}".strip() or owner.username,
                    'email': owner.email
                },
                'opportunity_count': owner_opps.count(),
                'total_value': float(total_value),
                'weighted_value': float(weighted_value),
                'win_rate': round(win_rate, 1)
            })

        # Sort by total value descending
        data.sort(key=lambda x: x['total_value'], reverse=True)

        return Response({'success': True, 'data': data})


class ProposalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Proposal model with CRUD operations.
    """
    queryset = Proposal.objects.select_related('opportunity', 'prepared_by', 'approved_by').all()
    serializer_class = ProposalSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'opportunity']
    search_fields = ['proposal_number', 'title']
    ordering_fields = ['created_at', 'sent_date', 'total_value']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark proposal as sent"""
        proposal = self.get_object()

        if proposal.status != 'DRAFT' and proposal.status != 'REVIEW':
            return Response(
                {'error': 'Only draft or reviewed proposals can be sent'},
                status=status.HTTP_400_BAD_REQUEST
            )

        proposal.status = 'SENT'
        proposal.sent_date = timezone.now().date()
        proposal.save()

        return Response(ProposalSerializer(proposal).data)


class ContractViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Contract model with CRUD operations.
    """
    queryset = Contract.objects.select_related('client', 'proposal').all()
    serializer_class = ContractSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'contract_type', 'client']
    search_fields = ['contract_number', 'title']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'contract_value']
    ordering = ['-created_at']


class ActivityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Activity model with CRUD operations.
    """
    queryset = Activity.objects.select_related('opportunity', 'created_by').all()
    serializer_class = ActivitySerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['opportunity', 'activity_type']
    search_fields = ['description', 'outcome']
    ordering_fields = ['activity_date', 'created_at']
    ordering = ['-activity_date']

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
