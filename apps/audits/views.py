from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
from .models import (
    Audit, AuditFinding, ISOStandard, AuditChecklist, ChecklistSection,
    AuditChecklistResponse, ChecklistEvidence, AuditDocument
)
from .serializers import (
    AuditSerializer, AuditFindingSerializer, ISOStandardSerializer,
    AuditChecklistSerializer, ChecklistSectionSerializer,
    AuditChecklistResponseSerializer, ChecklistEvidenceSerializer, AuditDocumentSerializer
)


class ISOStandardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ISO Standards.
    Provides CRUD operations for ISO certification standards.
    """
    queryset = ISOStandard.objects.filter(is_active=True)
    serializer_class = ISOStandardSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['code']


class AuditViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Audit management.
    Provides CRUD operations and custom actions for audits.

    Endpoints:
    - GET /api/v1/audits/ - List all audits
    - POST /api/v1/audits/ - Create new audit
    - GET /api/v1/audits/{id}/ - Get audit details
    - PUT /api/v1/audits/{id}/ - Update audit
    - DELETE /api/v1/audits/{id}/ - Delete audit
    - GET /api/v1/audits/stats/ - Get audit statistics
    - GET /api/v1/audits/calendar/ - Get calendar view data
    - GET /api/v1/audits/revenue/ - Get revenue data
    """
    queryset = Audit.objects.select_related(
        'client', 'iso_standard', 'lead_auditor', 'created_by'
    ).prefetch_related('auditors', 'findings', 'audit_templates', 'checklist_responses')
    serializer_class = AuditSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'audit_type', 'client', 'iso_standard', 'lead_auditor']
    search_fields = ['audit_number', 'title', 'client__name', 'description']
    ordering_fields = ['planned_start_date', 'created_at', 'audit_number']
    ordering = ['-planned_start_date']

    def perform_create(self, serializer):
        # Set created_by if user is authenticated
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    def perform_update(self, serializer):
        """Update an audit and ensure a corresponding Certification exists when certificates are issued."""
        audit = serializer.save()

        # Auto-create or sync Certification when certificate fields are present
        from apps.certifications.models import Certification

        if (
            audit.certificate_number
            and audit.certificate_issue_date
            and audit.certificate_expiry_date
        ):
            # Defaults for creating or updating the linked Certification
            defaults = {
                "client": audit.client,
                "iso_standard": audit.iso_standard,
                "audit": audit,
                "issue_date": audit.certificate_issue_date,
                "expiry_date": audit.certificate_expiry_date,
                "scope": audit.scope,
                "lead_auditor": audit.lead_auditor,
                # New certifications should be active so they appear in surveillance
                "status": "active",
                "created_by": self.request.user if getattr(self, "request", None) and self.request.user.is_authenticated else None,
            }

            certification, created = Certification.objects.get_or_create(
                certificate_number=audit.certificate_number,
                defaults=defaults,
            )

            if not created:
                # Update existing certification fields if they have changed
                changed = False
                for field, value in defaults.items():
                    # Don't overwrite created_by once set
                    if field == "created_by":
                        continue
                    if getattr(certification, field) != value:
                        setattr(certification, field, value)
                        changed = True
                if changed:
                    certification.save()


    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get audit statistics for dashboard.
        Returns counts by status, completion metrics, etc.
        """
        total_audits = self.get_queryset().count()

        # Count by status
        scheduled = self.get_queryset().filter(status='PLANNED').count()
        in_progress = self.get_queryset().filter(status='IN_PROGRESS').count()
        completed = self.get_queryset().filter(status='COMPLETED').count()

        # This month's completed audits
        this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        completed_this_month = self.get_queryset().filter(
            status='COMPLETED',
            actual_end_date__gte=this_month_start
        ).count()

        # Overdue audits (planned end date passed but not completed)
        overdue = self.get_queryset().filter(
            status__in=['PLANNED', 'IN_PROGRESS'],
            planned_end_date__lt=timezone.now().date()
        ).count()

        # Findings statistics
        findings_stats = self.get_queryset().aggregate(
            total_findings=Sum('findings_count'),
            total_major=Sum('major_findings'),
            total_minor=Sum('minor_findings'),
            total_opportunities=Sum('opportunities')
        )

        return Response({
            'success': True,
            'data': {
                'total': total_audits,
                'scheduled': scheduled,
                'in_progress': in_progress,
                'completed': completed,
                'completed_this_month': completed_this_month,
                'overdue': overdue,
                'findings': findings_stats
            }
        })

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """
        Get audits formatted for calendar view.
        Returns audits with date and auditor information.
        """
        # Get date range from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = self.get_queryset()

        if start_date and end_date:
            queryset = queryset.filter(
                planned_start_date__gte=start_date,
                planned_start_date__lte=end_date
            )

        audits = queryset.values(
            'id', 'audit_number', 'client__name', 'iso_standard__code',
            'audit_type', 'planned_start_date', 'planned_end_date',
            'lead_auditor__first_name', 'lead_auditor__last_name', 'status'
        )

        # Format for calendar
        calendar_data = []
        for audit in audits:
            calendar_data.append({
                'id': audit['id'],
                'audit_number': audit['audit_number'],
                'client': audit['client__name'],
                'standard': audit['iso_standard__code'],
                'type': audit['audit_type'],
                'start_date': audit['planned_start_date'],
                'end_date': audit['planned_end_date'],
                'auditor': f"{audit['lead_auditor__first_name']} {audit['lead_auditor__last_name']}".strip() if audit['lead_auditor__first_name'] else 'Unassigned',
                'status': audit['status']
            })

        return Response({
            'success': True,
            'data': calendar_data
        })

    @action(detail=False, methods=['get'])
    def surveillance(self, request):
        """
        Get surveillance audits for active certifications.
        Returns certifications with their surveillance schedule and upcoming audits.
        """
        from apps.certifications.models import Certification
        from datetime import date, timedelta

        # Get active certifications
        active_certs = Certification.objects.filter(
            status__in=['active', 'expiring-soon']
        ).select_related('client', 'iso_standard')

        surveillance_data = []

        for cert in active_certs:
            # Calculate surveillance dates based on issue date
            issue_date = cert.issue_date
            expiry_date = cert.expiry_date

            # Year 1 Surveillance (1 year after issue)
            year1_date = issue_date + timedelta(days=365)
            # Year 2 Surveillance (2 years after issue)
            year2_date = issue_date + timedelta(days=730)
            # Recertification (at expiry)
            recert_date = expiry_date

            # Determine status based on current date
            today = date.today()

            def get_surveillance_status(sched_date):
                if sched_date < today:
                    return 'overdue'
                elif sched_date <= today + timedelta(days=90):
                    return 'scheduled'
                else:
                    return 'pending'

            year1_status = get_surveillance_status(year1_date)
            year2_status = get_surveillance_status(year2_date)
            recert_status = get_surveillance_status(recert_date)

            surveillance_data.append({
                'id': str(cert.id),
                'certificate_number': cert.certificate_number,
                'client': {
                    'id': cert.client.id,
                    'name': cert.client.name
                },
                'iso_standard': {
                    'id': cert.iso_standard.id,
                    'code': cert.iso_standard.code,
                    'name': cert.iso_standard.name
                },
                'issue_date': cert.issue_date.isoformat(),
                'expiry_date': cert.expiry_date.isoformat(),
                'year1_surveillance': {
                    'date': year1_date.isoformat(),
                    'status': year1_status
                },
                'year2_surveillance': {
                    'date': year2_date.isoformat(),
                    'status': year2_status
                },
                'recertification': {
                    'date': recert_date.isoformat(),
                    'status': recert_status
                }
            })

        # Calculate statistics
        total_active = len(surveillance_data)
        scheduled_count = sum(1 for s in surveillance_data
                            if s['year1_surveillance']['status'] == 'scheduled' or
                               s['year2_surveillance']['status'] == 'scheduled' or
                               s['recertification']['status'] == 'scheduled')
        overdue_count = sum(1 for s in surveillance_data
                          if s['year1_surveillance']['status'] == 'overdue' or
                             s['year2_surveillance']['status'] == 'overdue' or
                             s['recertification']['status'] == 'overdue')

        # Get completed surveillance audits this year
        this_year_start = date.today().replace(month=1, day=1)
        completed_this_year = self.get_queryset().filter(
            status='COMPLETED',
            audit_type__in=['1st surveillance', '2nd surveillance', 'surveillance'],
            actual_end_date__gte=this_year_start
        ).count()

        return Response({
            'success': True,
            'data': {
                'certifications': surveillance_data,
                'stats': {
                    'active': total_active,
                    'scheduled_surveillance': scheduled_count,
                    'overdue_surveillance': overdue_count,
                    'completed_this_year': completed_this_year
                }
            }
        })

    @action(detail=False, methods=['get'])
    def revenue(self, request):
        """
        Get revenue data from audits.
        Note: This is a placeholder - actual revenue should come from invoices/payments.
        """
        # This would typically integrate with a finance/invoicing system
        # For now, return basic audit completion data
        completed_audits = self.get_queryset().filter(status='COMPLETED')

        return Response({
            'success': True,
            'data': {
                'total_completed': completed_audits.count(),
                'message': 'Revenue tracking requires integration with finance module'
            }
        })

    @action(detail=True, methods=['post', 'get'], url_path='checklist-responses')
    def checklist_responses(self, request, pk=None):
        """
        Handle checklist responses for an audit.
        POST: Save multiple checklist responses
        GET: Retrieve all checklist responses for an audit
        """
        audit = self.get_object()

        if request.method == 'POST':
            responses_data = request.data.get('responses', [])
            saved_responses = []

            for response_data in responses_data:
                response_data['audit'] = audit.id
                checklist_item_id = response_data.get('checklist_item_id')

                # Try to find existing response for this audit and checklist item
                try:
                    existing_response = AuditChecklistResponse.objects.get(
                        audit=audit,
                        checklist_item_id=checklist_item_id
                    )
                    # Update existing response
                    serializer = AuditChecklistResponseSerializer(
                        existing_response,
                        data=response_data,
                        partial=True
                    )
                except AuditChecklistResponse.DoesNotExist:
                    # Create new response
                    serializer = AuditChecklistResponseSerializer(data=response_data)

                if serializer.is_valid():
                    serializer.save()
                    saved_responses.append(serializer.data)
                else:
                    return Response(
                        {'error': 'Invalid response data', 'details': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response({
                'success': True,
                'message': f'{len(saved_responses)} responses saved',
                'data': saved_responses
            }, status=status.HTTP_200_OK)

        elif request.method == 'GET':
            responses = AuditChecklistResponse.objects.filter(audit=audit)
            serializer = AuditChecklistResponseSerializer(responses, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            })


class AuditFindingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Audit Findings.
    Provides CRUD operations for audit findings/non-conformances.

    Endpoints:
    - GET /api/v1/audit-findings/ - List all findings
    - POST /api/v1/audit-findings/ - Create new finding
    - GET /api/v1/audit-findings/{id}/ - Get finding details
    - PUT /api/v1/audit-findings/{id}/ - Update finding
    - DELETE /api/v1/audit-findings/{id}/ - Delete finding
    - GET /api/v1/audit-findings/stats/ - Get findings statistics
    """
    queryset = AuditFinding.objects.select_related(
        'audit', 'audit__client', 'verified_by'
    )
    serializer_class = AuditFindingSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['finding_type', 'status', 'audit', 'audit__client']
    search_fields = ['finding_number', 'description', 'clause_reference']
    ordering_fields = ['created_at', 'target_date', 'finding_number']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get findings statistics.
        Returns counts by severity and status.
        """
        total = self.get_queryset().count()

        # Count by finding type
        major = self.get_queryset().filter(finding_type='MAJOR').count()
        minor = self.get_queryset().filter(finding_type='MINOR').count()
        observations = self.get_queryset().filter(finding_type='OBSERVATION').count()
        opportunities = self.get_queryset().filter(finding_type='OPPORTUNITY').count()

        # Count by status
        open_findings = self.get_queryset().filter(status='OPEN').count()
        in_progress = self.get_queryset().filter(status='IN_PROGRESS').count()
        closed = self.get_queryset().filter(status='CLOSED').count()
        verified = self.get_queryset().filter(status='VERIFIED').count()

        return Response({
            'success': True,
            'data': {
                'total': total,
                'by_type': {
                    'major': major,
                    'minor': minor,
                    'observations': observations,
                    'opportunities': opportunities
                },
                'by_status': {
                    'open': open_findings,
                    'in_progress': in_progress,
                    'closed': closed,
                    'verified': verified
                }
            }
        })


class AuditChecklistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Audit Checklists.
    Provides CRUD operations for audit checklists and templates.
    """
    queryset = AuditChecklist.objects.select_related('iso_standard', 'created_by').prefetch_related('items')
    serializer_class = AuditChecklistSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['iso_standard', 'is_template']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        # Set created_by if user is authenticated
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def generate_pdf(self, request, pk=None):
        """
        Generate PDF report for an audit checklist template.

        GET /api/v1/audit-checklists/{id}/generate_pdf/
        """
        checklist = self.get_object()

        # Create PDF buffer
        buffer = BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        # Container for PDF elements
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=12,
            spaceBefore=12,
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
        )

        # Add title
        elements.append(Paragraph(checklist.title, title_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Add ISO Standard info
        if checklist.iso_standard:
            iso_info = f"<b>ISO Standard:</b> {checklist.iso_standard.code} - {checklist.iso_standard.name}"
            elements.append(Paragraph(iso_info, normal_style))
            elements.append(Spacer(1, 0.1 * inch))

        # Add description
        if checklist.description:
            elements.append(Paragraph(f"<b>Description:</b> {checklist.description}", normal_style))
            elements.append(Spacer(1, 0.2 * inch))

        # Add metadata
        created_date = checklist.created_at.strftime('%B %d, %Y')
        elements.append(Paragraph(f"<b>Created:</b> {created_date}", normal_style))
        if checklist.created_by:
            elements.append(Paragraph(f"<b>Created By:</b> {checklist.created_by.get_full_name() or checklist.created_by.username}", normal_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Add logo if available
        if hasattr(checklist, 'logo') and checklist.logo:
            try:
                from PIL import Image as PILImage
                logo_path = checklist.logo.path
                elements.append(Spacer(1, 0.1 * inch))
                # Add a placeholder for logo - ReportLab can handle this
                elements.append(Paragraph("<i>Company Logo</i>", normal_style))
                elements.append(Spacer(1, 0.1 * inch))
            except:
                pass

        # Add company information
        if hasattr(checklist, 'company_name') and checklist.company_name:
            elements.append(Paragraph(f"<b>Company:</b> {checklist.company_name}", normal_style))
            elements.append(Spacer(1, 0.1 * inch))

        # Add header content if available
        if hasattr(checklist, 'header_content') and checklist.header_content:
            elements.append(Paragraph(checklist.header_content, normal_style))
            elements.append(Spacer(1, 0.1 * inch))

        # Group items by section
        items = checklist.items.all().order_by('order')
        sections = {}
        for item in items:
            section_name = getattr(item, 'section_name', None) or "General Questions"
            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].append(item)

        # Render each section
        for section_name, section_items in sections.items():
            # Section header
            elements.append(Paragraph(f"Section: {section_name}", heading_style))
            elements.append(Spacer(1, 0.1 * inch))

            # Create table for this section
            table_data = [
                ['#', 'Clause', 'Type', 'Question', 'Compliance', 'Comments/Notes']
            ]

            for idx, item in enumerate(section_items, 1):
                # Enhanced compliance checkboxes based on template settings
                if hasattr(checklist, 'include_compliance_checkboxes') and checklist.include_compliance_checkboxes:
                    compliance = '☐ Compliant<br/>☐ Needs Improvement<br/>☐ Non-Compliant<br/>☐ N/A'
                else:
                    compliance = '☐ Yes<br/>☐ No<br/>☐ N/A'

                # Enhanced question with guidance and actions
                question_text = item.question
                if item.guidance:
                    question_text += f"<br/><br/><i><b>Guidance:</b> {item.guidance}</i>"

                # Add actions required if enabled and available
                if hasattr(item, 'actions_required') and item.actions_required and hasattr(checklist, 'enable_actions') and checklist.enable_actions:
                    question_text += f"<br/><br/><b>Actions Required:</b> {item.actions_required}"

                # Create question paragraph
                question_para = Paragraph(question_text, ParagraphStyle('QuestionText', parent=styles['Normal'], fontSize=9, leading=12))

                table_data.append([
                    str(idx),
                    (getattr(item, 'iso_clause', None) or item.clause_reference or '-'),
                    item.get_item_type_display(),
                    question_para,
                    Paragraph(compliance, ParagraphStyle('Compliance', parent=styles['Normal'], fontSize=7, leading=9)),
                    ''  # Empty column for handwritten comments/notes
                ])

            # Create and style table
            col_widths = [0.3*inch, 0.7*inch, 0.8*inch, 3.0*inch, 1.0*inch, 1.2*inch]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)

            # Get primary color for styling
            primary_color = getattr(checklist, 'primary_color', '#2563eb')
            try:
                table_header_color = colors.HexColor(primary_color)
            except:
                table_header_color = colors.HexColor('#2563eb')

            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), table_header_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))

        # Add signature section
        elements.append(PageBreak())
        elements.append(Paragraph("Audit Completion and Sign-off", heading_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Signature table
        signature_data = [
            ['Lead Auditor:', '______________________________', 'Date:', '_____________'],
            ['', '', '', ''],
            ['Auditee Representative:', '______________________________', 'Date:', '_____________'],
            ['', '', '', ''],
            ['Technical Expert (if applicable):', '______________________________', 'Date:', '_____________']
        ]

        signature_table = Table(signature_data, colWidths=[1.5*inch, 2.5*inch, 0.7*inch, 1.3*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(signature_table)

        # Add footer content if available
        if hasattr(checklist, 'footer_content') and checklist.footer_content:
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph(checklist.footer_content, normal_style))

        # Add generation timestamp
        from django.utils import timezone
        elements.append(Spacer(1, 0.3 * inch))
        generation_info = f"Generated on {timezone.now().strftime('%Y-%m-%d at %H:%M')} using Claude Code"
        elements.append(Paragraph(generation_info, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

        # Build PDF
        doc.build(elements)

        # Get PDF from buffer
        pdf = buffer.getvalue()
        buffer.close()

        # Create response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{checklist.title}.pdf"'
        response.write(pdf)

        return response


class ChecklistSectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Checklist Sections.
    Provides CRUD operations for organizing checklist items into sections.
    """
    queryset = ChecklistSection.objects.all()
    serializer_class = ChecklistSectionSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['checklist']
    ordering_fields = ['order', 'name']
    ordering = ['order']


class AuditChecklistResponseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Audit Checklist Responses.
    Provides CRUD operations for auditor responses to checklist items.
    """
    queryset = AuditChecklistResponse.objects.select_related(
        'audit', 'checklist_item', 'completed_by'
    ).prefetch_related('evidence_files')
    serializer_class = AuditChecklistResponseSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['audit', 'compliance_status', 'corrective_action_required', 'completed_by']
    search_fields = ['auditor_comments', 'auditor_notes', 'evidence_description']
    ordering_fields = ['completed_at', 'created_at', 'checklist_item__order']
    ordering = ['checklist_item__order']

    def perform_create(self, serializer):
        # Set completed_by to current user if authenticated
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(completed_by=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        # Update completed_at when response is modified
        from django.utils import timezone
        serializer.save(completed_at=timezone.now())

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Bulk update multiple checklist responses.
        Expects a list of response objects with id and updated fields.
        """
        responses_data = request.data.get('responses', [])
        updated_responses = []

        for response_data in responses_data:
            response_id = response_data.get('id')
            if response_id:
                try:
                    response = AuditChecklistResponse.objects.get(id=response_id)
                    serializer = self.get_serializer(response, data=response_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated_responses.append(serializer.data)
                except AuditChecklistResponse.DoesNotExist:
                    continue

        return Response({
            'success': True,
            'updated_count': len(updated_responses),
            'responses': updated_responses
        })

    @action(detail=False, methods=['get'])
    def progress(self, request):
        """
        Get checklist completion progress for an audit.
        """
        audit_id = request.query_params.get('audit')
        if not audit_id:
            return Response({'error': 'audit parameter is required'}, status=400)

        total_items = AuditChecklistResponse.objects.filter(audit_id=audit_id).count()
        completed_items = AuditChecklistResponse.objects.filter(
            audit_id=audit_id,
            compliance_status__isnull=False
        ).count()

        # Compliance breakdown
        compliance_counts = AuditChecklistResponse.objects.filter(
            audit_id=audit_id
        ).values('compliance_status').annotate(
            count=Count('compliance_status')
        )

        compliance_summary = {item['compliance_status'] or 'pending': item['count'] for item in compliance_counts}

        return Response({
            'success': True,
            'data': {
                'total_items': total_items,
                'completed_items': completed_items,
                'completion_percentage': round((completed_items / total_items * 100) if total_items > 0 else 0, 2),
                'compliance_summary': compliance_summary
            }
        })


class ChecklistEvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Checklist Evidence files.
    Provides CRUD operations for evidence file management.
    """
    queryset = ChecklistEvidence.objects.select_related('response', 'uploaded_by')
    serializer_class = ChecklistEvidenceSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['response', 'uploaded_by']
    ordering_fields = ['uploaded_at', 'filename']
    ordering = ['-uploaded_at']

    def perform_create(self, serializer):
        # Set file metadata and uploaded_by
        file_obj = self.request.FILES.get('file')
        if file_obj:
            serializer.save(
                filename=file_obj.name,
                original_name=file_obj.name,
                file_size=file_obj.size,
                uploaded_by=self.request.user if self.request.user.is_authenticated else None
            )
        else:
            serializer.save(
                uploaded_by=self.request.user if self.request.user.is_authenticated else None
            )


class AuditDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Audit Documents.
    Provides CRUD operations for audit-related documents.
    """
    queryset = AuditDocument.objects.all()
    serializer_class = AuditDocumentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['audit', 'category', 'uploaded_by']
    search_fields = ['filename', 'original_name', 'description']
    ordering_fields = ['uploaded_at', 'filename', 'file_size']
    ordering = ['-uploaded_at']

    def perform_create(self, serializer):
        # Set file metadata and uploaded_by
        file_obj = self.request.FILES.get('file')
        if file_obj:
            serializer.save(
                filename=file_obj.name,
                original_name=file_obj.name,
                file_size=file_obj.size,
                uploaded_by=self.request.user if self.request.user.is_authenticated else None
            )
        else:
            serializer.save(
                uploaded_by=self.request.user if self.request.user.is_authenticated else None
            )

