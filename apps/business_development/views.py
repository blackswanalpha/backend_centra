from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q, Avg
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime, timedelta
from io import BytesIO

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.pdfgen import canvas

from apps.business_development.models import Lead, Opportunity, Proposal, Contract, ContractTemplate, ActivityLog
from .serializers import (
    LeadSerializer, OpportunitySerializer, OpportunityListSerializer,
    ProposalSerializer, ContractSerializer, ActivityLogSerializer
)
from .contract_template_service import ContractTemplateService


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
    Supports comprehensive certification agreements with ISO standards.
    """
    queryset = Contract.objects.select_related('opportunity', 'opportunity__client', 'proposal').all()
    serializer_class = ContractSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'contract_type', 'opportunity', 'opportunity__client']
    search_fields = ['contract_number', 'title', 'client_organization', 'opportunity__title']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'contract_value', 'agreement_date']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get contract statistics by status"""
        contracts = self.filter_queryset(self.get_queryset())

        # Calculate contracts expiring within 30 days
        today = timezone.now().date()
        expiring_date = today + timedelta(days=30)

        # Count by status
        # Active: ACTIVE status and not expiring within 30 days
        active_count = contracts.filter(status='ACTIVE', end_date__gt=expiring_date).count()

        # Pending: DRAFT, UNDER_REVIEW, or PENDING_SIGNATURE
        pending_count = contracts.filter(
            status__in=['DRAFT', 'UNDER_REVIEW', 'PENDING_SIGNATURE']
        ).count()

        # Expiring: ACTIVE status and expiring within 30 days
        expiring_count = contracts.filter(
            status='ACTIVE',
            end_date__lte=expiring_date,
            end_date__gte=today
        ).count()

        # Expired: COMPLETED status or past end date (excluding TERMINATED and CANCELLED)
        expired_count = contracts.filter(
            Q(status='COMPLETED') | Q(end_date__lt=today)
        ).exclude(status__in=['TERMINATED', 'CANCELLED']).count()

        # Total contract value (only ACTIVE contracts)
        total_value = contracts.filter(status='ACTIVE').aggregate(
            total=Sum('contract_value')
        )['total'] or 0

        return Response({
            'success': True,
            'data': {
                'active': active_count,
                'pending': pending_count,
                'expiring': expiring_count,
                'expired': expired_count,
                'total_value': float(total_value),
                'total_count': contracts.count()
            }
        })
    
    @action(detail=True, methods=['post'])
    def generate_from_opportunity(self, request, pk=None):
        """Generate a contract from an opportunity"""
        try:
            opportunity = Opportunity.objects.select_related('client').get(pk=pk)
        except Opportunity.DoesNotExist:
            return Response(
                {'error': 'Opportunity not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create contract with pre-filled data from opportunity
        contract_data = {
            'opportunity_id': opportunity.id,
            'title': request.data.get('title', f"Certification Agreement - {opportunity.title}"),
            'contract_type': request.data.get('contract_type', 'CERTIFICATION'),
            'description': request.data.get('description', opportunity.description),
            'agreement_date': request.data.get('agreement_date', timezone.now().date()),
            'client_organization': opportunity.client.name if opportunity.client else '',
            'client_email': getattr(opportunity.client, 'email', ''),
            'iso_standards': request.data.get('iso_standards', []),
            'scope_of_work': request.data.get('scope_of_work', ''),
            'start_date': request.data.get('start_date'),
            'end_date': request.data.get('end_date'),
            'fee_per_standard_year_1': request.data.get('fee_per_standard_year_1', 1000),
            'fee_per_standard_year_2': request.data.get('fee_per_standard_year_2', 1000),
            'fee_per_standard_year_3': request.data.get('fee_per_standard_year_3', 1000),
            'contract_value': request.data.get('contract_value', opportunity.estimated_value),
            'currency': request.data.get('currency', opportunity.currency),
            'payment_schedule': request.data.get('payment_schedule', ''),
        }
        
        serializer = self.get_serializer(data=contract_data)
        if serializer.is_valid():
            serializer.save(created_by=request.user if request.user.is_authenticated else None)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _generate_contract_pdf(self, contract):
        """
        Helper function to generate complete contract PDF using ReportLab.
        Returns PDF bytes.
        """
        # Create PDF buffer
        buffer = BytesIO()
        
        # Create PDF document with professional margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=60,
            bottomMargin=40,
        )
        
        # Container for PDF elements
        elements = []
        
        # Define comprehensive styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'ContractTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'ContractSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'ContractHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'ContractSubheading',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'ContractNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14,
            textColor=colors.HexColor('#1f2937')
        )
        
        # ===== HEADER SECTION =====
        elements.append(Paragraph("CERTIFICATION AGREEMENT", title_style))
        elements.append(Paragraph(f"Contract No: {contract.contract_number} | ID: {contract.id}", subtitle_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # ===== CONTRACT DETAILS SECTION =====
        elements.append(Paragraph("1. Contract Details", heading_style))
        contract_details = [
            ['Contract Type:', contract.get_contract_type_display()],
            ['Title:', Paragraph(contract.title, normal_style)],
            ['Description:', Paragraph(contract.description[:200] + '...' if len(contract.description) > 200 else contract.description, normal_style) if contract.description else 'N/A'],
            ['Agreement Date:', contract.agreement_date.strftime('%B %d, %Y') if contract.agreement_date else 'To be determined'],
            ['Status:', contract.get_status_display()],
        ]
        
        details_table = Table(contract_details, colWidths=[2*inch, 4.5*inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.2 * inch))
        
        # ===== CLIENT INFORMATION SECTION =====
        elements.append(Paragraph("2. Client Information", heading_style))
        client_info = [
            ['Organization:', contract.client_organization],
            ['Contact Person:', contract.client_contact_person or 'N/A'],
            ['Email:', contract.client_email],
            ['Secondary Email:', contract.client_secondary_email or 'N/A'],
            ['Telephone:', contract.client_telephone or 'N/A'],
            ['Website:', contract.client_website or 'N/A'],
            ['Address:', Paragraph(contract.client_address or 'N/A', normal_style)],
            ['Site(s) Covered:', Paragraph(contract.site_covered or 'N/A', normal_style)],
        ]
        
        client_table = Table(client_info, colWidths=[2*inch, 4.5*inch])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 0.2 * inch))
        
        # ===== CERTIFICATION BODY SECTION =====
        elements.append(Paragraph("3. Certification Body", heading_style))
        cb_info = [
            ['Name:', contract.cb_name],
            ['Address:', Paragraph(contract.cb_address, normal_style)],
            ['Role:', Paragraph(contract.cb_role, normal_style)],
        ]
        
        cb_table = Table(cb_info, colWidths=[2*inch, 4.5*inch])
        cb_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(cb_table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # ===== SCOPE OF CERTIFICATION SECTION =====
        elements.append(Paragraph("4. Scope of Certification", heading_style))
        
        if contract.iso_standards:
            elements.append(Paragraph("<b>ISO Standards:</b>", subheading_style))
            for standard in contract.iso_standards:
                elements.append(Paragraph(f"• {standard}", normal_style))
            elements.append(Spacer(1, 0.1 * inch))
        
        elements.append(Paragraph("<b>Scope of Work:</b>", subheading_style))
        scope_text = contract.scope_of_work or 'To be defined based on client requirements and certification standards.'
        elements.append(Paragraph(scope_text, normal_style))
        elements.append(Spacer(1, 0.25 * inch))
        
        # ===== TIMELINE & DURATION SECTION =====
        elements.append(Paragraph("5. Timeline & Duration", heading_style))
        timeline_info = [
            ['Start Date:', contract.start_date.strftime('%B %d, %Y')],
            ['End Date:', contract.end_date.strftime('%B %d, %Y')],
            ['Contract Duration:', f"{contract.duration_months} months ({contract.duration_months // 12} years)"],
            ['Certification Cycle:', f"{contract.certification_cycle_years} years"],
            ['Stage I & II Gap (Max):', f"{contract.stage_1_stage_2_max_gap_days} days"],
            ['NC Closure Period (Max):', f"{contract.nc_closure_max_days} days"],
            ['Certificate Issue Time:', f"{contract.certificate_issue_days} working days after NC closure"],
            ['Certificate Validity:', f"{contract.certificate_validity_years} years (with annual surveillance)"],
        ]
        
        timeline_table = Table(timeline_info, colWidths=[2.5*inch, 4*inch])
        timeline_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(timeline_table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # ===== PAGE BREAK =====
        elements.append(PageBreak())
        
        # ===== CERTIFICATION AUDIT PROCESS SECTION =====
        elements.append(Paragraph("6. Certification Audit Process", heading_style))
        
        # Stage I Audit
        elements.append(Paragraph("6.1 Stage I Audit (Documentation Review)", subheading_style))
        stage1_data = [
            ['Duration:', f"{contract.stage_1_audit_days} day(s)"],
            ['Remote Option:', 'Yes - Can be conducted remotely' if contract.stage_1_remote_allowed else 'No - Must be on-site'],
            ['Description:', Paragraph(contract.stage_1_audit_description, normal_style)],
        ]
        stage1_table = Table(stage1_data, colWidths=[1.5*inch, 5*inch])
        stage1_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(stage1_table)
        elements.append(Spacer(1, 0.15 * inch))
        
        # Stage II Audit
        elements.append(Paragraph("6.2 Stage II Audit (Implementation Assessment)", subheading_style))
        stage2_data = [
            ['Duration:', f"{contract.stage_2_audit_days} day(s)"],
            ['Description:', Paragraph(contract.stage_2_audit_description, normal_style)],
        ]
        stage2_table = Table(stage2_data, colWidths=[1.5*inch, 5*inch])
        stage2_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(stage2_table)
        elements.append(Spacer(1, 0.15 * inch))
        
        # Surveillance Audits
        elements.append(Paragraph("6.3 Surveillance Audits", subheading_style))
        surveillance_data = [
            ['Frequency:', contract.surveillance_audit_frequency],
            ['Description:', Paragraph(contract.surveillance_audit_description, normal_style)],
        ]
        surveillance_table = Table(surveillance_data, colWidths=[1.5*inch, 5*inch])
        surveillance_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(surveillance_table)
        elements.append(Spacer(1, 0.15 * inch))
        
        # Recertification Audit
        elements.append(Paragraph("6.4 Recertification Audit", subheading_style))
        recert_data = [
            ['Timing:', contract.recertification_audit_timing],
            ['Description:', Paragraph(contract.recertification_audit_description, normal_style)],
        ]
        recert_table = Table(recert_data, colWidths=[1.5*inch, 5*inch])
        recert_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(recert_table)
        elements.append(Spacer(1, 0.25 * inch))
        
        # ===== FINANCIAL TERMS SECTION =====
        elements.append(Paragraph("7. Financial Terms", heading_style))
        
        # Fee Structure Table
        fee_data = [
            ['Description', 'Amount'],
            ['Year 1 Certification Fee (per standard)', f"{contract.currency} {contract.fee_per_standard_year_1:,.2f}"],
            ['Year 2 Surveillance Fee (per standard)', f"{contract.currency} {contract.fee_per_standard_year_2:,.2f}"],
            ['Year 3 Surveillance Fee (per standard)', f"{contract.currency} {contract.fee_per_standard_year_3:,.2f}"],
            ['', ''],
            ['Total Number of Standards', str(contract.total_standards_count)],
            ['', ''],
            ['Total Year 1 Fee', f"{contract.currency} {contract.total_year_1_fee:,.2f}"],
            ['Total Year 2 Fee', f"{contract.currency} {contract.total_year_2_fee:,.2f}"],
            ['Total Year 3 Fee', f"{contract.currency} {contract.total_year_3_fee:,.2f}"],
            ['', ''],
            ['TOTAL CONTRACT VALUE', f"{contract.currency} {contract.contract_value:,.2f}"],
        ]
        
        fee_table = Table(fee_data, colWidths=[4*inch, 2.5*inch])
        fee_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        elements.append(fee_table)
        elements.append(Spacer(1, 0.15 * inch))
        
        # Payment Schedule
        if contract.payment_schedule:
            elements.append(Paragraph("<b>Payment Schedule:</b>", subheading_style))
            elements.append(Paragraph(contract.payment_schedule, normal_style))
            elements.append(Spacer(1, 0.1 * inch))
        
        # Additional Fees
        if contract.additional_fees_description:
            elements.append(Paragraph("<b>Additional Fees May Apply For:</b>", subheading_style))
            elements.append(Paragraph(contract.additional_fees_description, normal_style))
            elements.append(Spacer(1, 0.1 * inch))
        
        # Recertification Fee
        if contract.recertification_fee_tbd:
            elements.append(Paragraph("<b>Recertification Fee:</b> To be determined based on scope at time of recertification", normal_style))
        elif contract.recertification_fee:
            elements.append(Paragraph(f"<b>Recertification Fee:</b> {contract.currency} {contract.recertification_fee:,.2f}", normal_style))
        
        elements.append(Spacer(1, 0.25 * inch))
        
        # ===== PAGE BREAK =====
        elements.append(PageBreak())
        
        # ===== TERMS & CONDITIONS SECTION =====
        elements.append(Paragraph("8. Terms & Conditions", heading_style))
        
        # Cancellation Policy
        elements.append(Paragraph("8.1 Cancellation & Rescheduling Policy", subheading_style))
        elements.append(Paragraph(
            f"• Notice required for cancellation or rescheduling: <b>{contract.cancellation_notice_days} working days</b>",
            normal_style
        ))
        elements.append(Paragraph(
            f"• Late cancellation fee: <b>{'Full audit fee applies' if contract.cancellation_fee_applies else 'No fee'}</b>",
            normal_style
        ))
        elements.append(Spacer(1, 0.15 * inch))
        
        # Confidentiality
        elements.append(Paragraph("8.2 Confidentiality", subheading_style))
        elements.append(Paragraph(contract.confidentiality_clause, normal_style))
        elements.append(Spacer(1, 0.15 * inch))
        
        # Data Protection
        elements.append(Paragraph("8.3 Data Protection", subheading_style))
        elements.append(Paragraph(contract.data_protection_compliance, normal_style))
        elements.append(Spacer(1, 0.15 * inch))
        
        # Client Responsibilities
        if contract.client_responsibilities:
            elements.append(Paragraph("8.4 Client Responsibilities", subheading_style))
            for idx, responsibility in enumerate(contract.client_responsibilities, 1):
                elements.append(Paragraph(f"{idx}. {responsibility}", normal_style))
            elements.append(Spacer(1, 0.15 * inch))
        
        # Termination & Renewal
        elements.append(Paragraph("8.5 Termination & Renewal", subheading_style))
        elements.append(Paragraph(
            f"• Either party may terminate with <b>{contract.termination_notice_days} days</b> written notice",
            normal_style
        ))
        elements.append(Paragraph(
            f"• Termination {'does not' if not contract.termination_fee_waiver else 'does'} waive fees for completed or confirmed audits",
            normal_style
        ))
        elements.append(Paragraph(
            f"• Auto-renewal: <b>{'Yes' if contract.auto_renewal else 'No'}</b>",
            normal_style
        ))
        if contract.auto_renewal:
            elements.append(Paragraph(
                f"• Renewal notice period: <b>{contract.renewal_notice_days} days</b>",
                normal_style
            ))
        elements.append(Spacer(1, 0.15 * inch))
        
        # Entire Agreement
        elements.append(Paragraph("8.6 Entire Agreement", subheading_style))
        elements.append(Paragraph(contract.entire_agreement_clause, normal_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # ===== SIGNATURES SECTION =====
        elements.append(Paragraph("9. Signatures", heading_style))
        elements.append(Spacer(1, 0.15 * inch))
        
        signature_data = [
            ['CLIENT REPRESENTATIVE', 'CERTIFICATION BODY REPRESENTATIVE'],
            ['', ''],
            [f"Name: {contract.signed_by_client_name or '_' * 35}", f"Name: {contract.signed_by_company_name}"],
            ['', ''],
            [f"Position: {contract.signed_by_client_position or '_' * 35}", f"Position: {contract.signed_by_company_position}"],
            ['', ''],
            [f"Date: {contract.client_signed_date.strftime('%B %d, %Y') if contract.client_signed_date else '_' * 25}", 
             f"Date: {contract.company_signed_date.strftime('%B %d, %Y') if contract.company_signed_date else '_' * 25}"],
            ['', ''],
            ['', ''],
            ['Signature: ________________________', 'Signature: ________________________'],
        ]
        
        signature_table = Table(signature_data, colWidths=[3.25*inch, 3.25*inch])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#2563eb')),
        ]))
        elements.append(signature_table)
        
        # ===== FOOTER =====
        elements.append(Spacer(1, 0.4 * inch))
        generation_info = f"Document generated on {timezone.now().strftime('%B %d, %Y at %H:%M UTC')} | Contract ID: {contract.id}"
        elements.append(Paragraph(
            generation_info,
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def download_pdf(self, request, pk=None):
        """
        Generate and download complete contract PDF.
        
        GET /api/v1/contracts/{id}/download_pdf/
        """
        contract = self.get_object()
        
        # Generate PDF
        pdf_bytes = self._generate_contract_pdf(contract)
        
        # Create response with contract ID in filename
        response = HttpResponse(content_type='application/pdf')
        filename = f"contract_{contract.id}_{contract.contract_number}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_bytes)
        
        return response
    
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def send_email(self, request, pk=None):
        """
        Send complete contract PDF via email.
        
        POST /api/v1/contracts/{id}/send_email/
        Body: {
            "recipient_email": "client@example.com",
            "recipient_name": "John Doe",
            "subject": "Your Contract Agreement",
            "message": "Custom message (optional)"
        }
        """
        contract = self.get_object()
        
        # Get email parameters from request
        recipient_email = request.data.get('recipient_email', contract.client_email)
        recipient_name = request.data.get('recipient_name', contract.client_contact_person or 'Valued Client')
        subject = request.data.get('subject', f'Certification Agreement - Contract {contract.contract_number}')
        custom_message = request.data.get('message', '')
        
        if not recipient_email:
            return Response(
                {'error': 'Recipient email is required. Please provide recipient_email in the request body or ensure the contract has a client email.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate complete PDF using the helper function
        try:
            pdf_bytes = self._generate_contract_pdf(contract)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Compose professional email body
        email_body = f"""Dear {recipient_name},

{custom_message if custom_message else 'Please find attached your certification agreement contract for review and signature.'}

CONTRACT SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Contract ID: {contract.id}
Contract Number: {contract.contract_number}
Client Organization: {contract.client_organization}
Contract Type: {contract.get_contract_type_display()}

ISO Standards: {', '.join(contract.iso_standards) if contract.iso_standards else 'To be determined'}
Contract Value: {contract.currency} {contract.contract_value:,.2f}

Contract Period: {contract.start_date.strftime('%B %d, %Y')} to {contract.end_date.strftime('%B %d, %Y')}
Duration: {contract.duration_months} months ({contract.duration_months // 12} years)

Status: {contract.get_status_display()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS:
1. Review the attached contract document carefully
2. If you have any questions or require clarifications, please contact us
3. Once satisfied, please sign and return the contract
4. We will countersign and provide you with the fully executed agreement

CONTACT INFORMATION:
{contract.cb_name}
{contract.cb_address}

If you have any questions or concerns regarding this contract, please don't hesitate to contact us.

Best regards,
{contract.cb_name}
Certification Services Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message. Please do not reply directly to this email.
Document generated on {timezone.now().strftime('%B %d, %Y at %H:%M UTC')}
        """
        
        # Create email with professional formatting
        try:
            email = EmailMessage(
                subject=subject,
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@assurehub.com',
                to=[recipient_email],
                reply_to=[contract.client_email] if contract.client_email else None,
            )
            
            # Attach PDF with contract ID in filename
            filename = f"contract_{contract.id}_{contract.contract_number}.pdf"
            email.attach(filename, pdf_bytes, 'application/pdf')
            
            # Send email
            email.send(fail_silently=False)
            
            return Response({
                'success': True,
                'message': f'Contract successfully sent to {recipient_email}',
                'details': {
                    'contract_id': contract.id,
                    'contract_number': contract.contract_number,
                    'recipient': recipient_email,
                    'subject': subject,
                    'attachment': filename
                }
            })
            
        except Exception as e:
            return Response(
                {
                    'error': f'Failed to send email: {str(e)}',
                    'details': 'Please check your email configuration and try again.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActivityLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ActivityLog model with CRUD operations.
    """
    queryset = ActivityLog.objects.select_related('lead', 'opportunity', 'client', 'performed_by').all()
    serializer_class = ActivityLogSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activity_type', 'lead', 'opportunity', 'client', 'performed_by']
    search_fields = ['subject', 'description']
    ordering_fields = ['activity_date', 'created_at']
    ordering = ['-activity_date']

    def perform_create(self, serializer):
        """Set performed_by to current user"""
        serializer.save(performed_by=self.request.user if self.request.user.is_authenticated else None)


class ContractTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ContractTemplate model with CRUD operations.
    Handles template creation, updates, and contract generation from templates.
    """
    queryset = ContractTemplate.objects.select_related('created_by').all()
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['template_type', 'status', 'is_active', 'is_default']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        # For now, return a basic dict response. In production, create proper serializers
        return None

    def list(self, request):
        """List all contract templates"""
        try:
            templates = ContractTemplateService.list_templates(
                template_type=request.query_params.get('template_type'),
                is_active=request.query_params.get('is_active', 'true').lower() == 'true'
            )
            
            template_data = []
            for template in templates:
                template_data.append({
                    'id': template.id,
                    'template_id': template.template_id,
                    'name': template.name,
                    'description': template.description,
                    'template_type': template.template_type,
                    'status': template.status,
                    'is_active': template.is_active,
                    'is_default': template.is_default,
                    'version': template.version,
                    'created_at': template.created_at,
                    'updated_at': template.updated_at,
                })
            
            return Response({
                'success': True,
                'data': template_data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """Get a specific contract template"""
        try:
            template = ContractTemplate.objects.get(template_id=pk)
            
            return Response({
                'success': True,
                'data': {
                    'id': template.id,
                    'template_id': template.template_id,
                    'name': template.name,
                    'description': template.description,
                    'template_type': template.template_type,
                    'template_data': template.template_data,
                    'status': template.status,
                    'is_active': template.is_active,
                    'is_default': template.is_default,
                    'version': template.version,
                    'created_at': template.created_at,
                    'updated_at': template.updated_at,
                }
            })
            
        except ContractTemplate.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Template not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """Create a new contract template from template builder data"""
        try:
            template_data = request.data.get('template_data', {})
            
            if not template_data:
                return Response({
                    'success': False,
                    'error': 'Template data is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the template
            template = ContractTemplateService.create_contract_template(
                template_data=template_data,
                created_by=request.user if request.user.is_authenticated else None
            )
            
            return Response({
                'success': True,
                'message': 'Template created successfully',
                'data': {
                    'id': template.id,
                    'template_id': template.template_id,
                    'name': template.name,
                    'template_type': template.template_type,
                    'status': template.status,
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        """Update an existing contract template"""
        try:
            template_data = request.data.get('template_data', {})
            
            if not template_data:
                return Response({
                    'success': False,
                    'error': 'Template data is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the template
            template = ContractTemplateService.update_contract_template(
                template_id=pk,
                template_data=template_data
            )
            
            return Response({
                'success': True,
                'message': 'Template updated successfully',
                'data': {
                    'id': template.id,
                    'template_id': template.template_id,
                    'name': template.name,
                    'template_type': template.template_type,
                    'status': template.status,
                    'updated_at': template.updated_at,
                }
            })
            
        except ContractTemplate.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Template not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def generate_contract(self, request, pk=None):
        """Generate a new contract from this template"""
        try:
            opportunity_id = request.data.get('opportunity_id')
            contract_data = request.data.get('contract_data', {})
            
            # Generate the contract
            contract = ContractTemplateService.generate_contract_from_template(
                template_id=pk,
                opportunity_id=opportunity_id,
                contract_data=contract_data,
                created_by=request.user if request.user.is_authenticated else None
            )
            
            return Response({
                'success': True,
                'message': 'Contract generated successfully',
                'data': {
                    'contract_id': contract.id,
                    'contract_number': contract.contract_number,
                    'title': contract.title,
                    'status': contract.status,
                    'client_organization': contract.client_organization,
                    'contract_value': float(contract.contract_value),
                }
            }, status=status.HTTP_201_CREATED)
            
        except ContractTemplate.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Template not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export template as JSON"""
        try:
            template_json = ContractTemplateService.export_template_to_json(pk)
            
            return Response({
                'success': True,
                'data': template_json
            })
            
        except ContractTemplate.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Template not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def import_template(self, request):
        """Import template from JSON"""
        try:
            template_json = request.data.get('template_json', {})
            
            if not template_json:
                return Response({
                    'success': False,
                    'error': 'Template JSON is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Import the template
            template = ContractTemplateService.import_template_from_json(
                template_json=template_json,
                created_by=request.user if request.user.is_authenticated else None
            )
            
            return Response({
                'success': True,
                'message': 'Template imported successfully',
                'data': {
                    'id': template.id,
                    'template_id': template.template_id,
                    'name': template.name,
                    'template_type': template.template_type,
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def default_template(self, request):
        """Get the default template for a specific type"""
        try:
            template_type = request.query_params.get('template_type', 'CERTIFICATION_CONTRACT')
            
            template = ContractTemplateService.get_default_template(template_type)
            
            if not template:
                return Response({
                    'success': False,
                    'error': f'No default template found for type: {template_type}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'data': {
                    'id': template.id,
                    'template_id': template.template_id,
                    'name': template.name,
                    'description': template.description,
                    'template_type': template.template_type,
                    'template_data': template.template_data,
                    'version': template.version,
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
