"""
Management command to load certificate templates into the database.
"""

from django.core.management.base import BaseCommand
from django.core.files import File
from apps.certifications.models import CertificateTemplate
from apps.audits.models import ISOStandard
import os


class Command(BaseCommand):
    help = 'Load certificate templates into the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading certificate templates...'))
        
        # Common variables for all templates
        common_variables = {
            'client_name': 'Client organization name',
            'client_address': 'Client full address',
            'client_email': 'Client email address',
            'client_phone': 'Client phone number',
            'iso_standard_code': 'ISO standard code',
            'iso_standard_name': 'ISO standard full name',
            'certificate_number': 'Unique certificate number',
            'issue_date': 'Certificate issue date',
            'expiry_date': 'Certificate expiry date',
            'scope': 'Certification scope description',
            'certification_body': 'Name of certification body',
            'accreditation_number': 'Accreditation number',
            'lead_auditor_name': 'Lead auditor full name',
            'lead_auditor_email': 'Lead auditor email',
        }

        # Define templates to load
        templates = [
            {
                'name': 'ISO 9001:2015 Quality Management Certificate',
                'description': 'Professional certificate template for ISO 9001:2015 Quality Management System',
                'template_type': 'docx',
                'iso_standard_code': 'ISO 9001:2015',
                'file_path': 'media/certificate_templates/samples/ISO_9001_2015_Certificate_Template.docx',
                'is_active': True,
                'is_default': True,
                'variables': common_variables,
            },
            {
                'name': 'ISO 14001:2015 Environmental Management Certificate',
                'description': 'Professional certificate template for ISO 14001:2015 Environmental Management System',
                'template_type': 'docx',
                'iso_standard_code': 'ISO 14001:2015',
                'file_path': 'media/certificate_templates/samples/ISO_14001_2015_Certificate_Template.docx',
                'is_active': True,
                'is_default': True,
                'variables': common_variables,
            },
            {
                'name': 'ISO 45001:2018 Occupational Health & Safety Certificate',
                'description': 'Professional certificate template for ISO 45001:2018 OH&S Management System',
                'template_type': 'docx',
                'iso_standard_code': 'ISO 45001:2018',
                'file_path': 'media/certificate_templates/samples/ISO_45001_2018_Certificate_Template.docx',
                'is_active': True,
                'is_default': True,
                'variables': common_variables,
            },
            {
                'name': 'ISO 27001:2013 Information Security Certificate',
                'description': 'Professional certificate template for ISO 27001:2013 Information Security Management System',
                'template_type': 'docx',
                'iso_standard_code': 'ISO 27001:2013',
                'file_path': 'media/certificate_templates/samples/ISO_27001_2013_Certificate_Template.docx',
                'is_active': True,
                'is_default': True,
                'variables': common_variables,
            },
            {
                'name': 'ISO 22301:2019 Business Continuity Certificate',
                'description': 'Professional certificate template for ISO 22301:2019 Business Continuity Management System',
                'template_type': 'docx',
                'iso_standard_code': 'ISO 22301:2019',
                'file_path': 'media/certificate_templates/samples/ISO_22301_2019_Certificate_Template.docx',
                'is_active': True,
                'is_default': True,
                'variables': common_variables,
            },
        ]
        
        loaded_count = 0
        skipped_count = 0
        
        for template_data in templates:
            try:
                # Get ISO standard
                iso_standard = ISOStandard.objects.filter(
                    code=template_data['iso_standard_code']
                ).first()
                
                if not iso_standard:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ ISO Standard {template_data['iso_standard_code']} not found. Skipping template."
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Check if file exists
                file_path = template_data['file_path']
                if not os.path.exists(file_path):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ Template file not found: {file_path}. Skipping."
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Check if template already exists
                existing = CertificateTemplate.objects.filter(
                    name=template_data['name'],
                    iso_standard=iso_standard
                ).first()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ Template '{template_data['name']}' already exists. Skipping."
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Create template
                template = CertificateTemplate(
                    name=template_data['name'],
                    description=template_data['description'],
                    template_type=template_data['template_type'],
                    iso_standard=iso_standard,
                    is_active=template_data['is_active'],
                    is_default=template_data['is_default'],
                    variables=template_data['variables']
                )
                
                # Attach file
                with open(file_path, 'rb') as f:
                    template.template_file.save(
                        os.path.basename(file_path),
                        File(f),
                        save=True
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Loaded template: {template_data['name']}"
                    )
                )
                loaded_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Error loading template '{template_data['name']}': {str(e)}"
                    )
                )
                skipped_count += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {loaded_count} template(s)'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped {skipped_count} template(s)'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Template loading complete!'))

