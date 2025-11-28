"""
Contract Template Service
Handles integration between Template Builder and Business Development Contract system
"""

from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date
import json
import uuid

from .models import Contract, ContractTemplate


class ContractTemplateService:
    """Service for managing contract templates and generating contracts from templates"""
    
    @staticmethod
    def create_contract_template(template_data: dict, created_by: User = None) -> ContractTemplate:
        """
        Create a new contract template from template builder data
        
        Args:
            template_data (dict): Complete template data from template builder
            created_by (User): User who created the template
            
        Returns:
            ContractTemplate: Created template instance
        """
        with transaction.atomic():
            # Extract metadata from template
            metadata = template_data.get('metadata', {})
            template_type = metadata.get('templateType', 'CERTIFICATION_CONTRACT')
            
            # Generate unique template ID if not provided
            template_id = template_data.get('id', str(uuid.uuid4()))
            
            # Generate unique version string using timestamp to avoid duplicate key constraint
            # Format: 1.0.YYYYMMDDHHMMSS
            version_timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_version = f"1.0.{version_timestamp}"
            
            # Create the template
            contract_template = ContractTemplate.objects.create(
                template_id=template_id,
                name=template_data.get('title', 'Untitled Contract Template'),
                description=template_data.get('description', ''),
                template_type=template_type.upper(),
                template_data=template_data,
                version=unique_version,  # Use unique version
                created_by=created_by,
                status='PUBLISHED' if template_data.get('is_published') else 'DRAFT'
            )
            
            return contract_template
    
    @staticmethod
    def update_contract_template(template_id: str, template_data: dict) -> ContractTemplate:
        """
        Update an existing contract template
        
        Args:
            template_id (str): Template ID to update
            template_data (dict): Updated template data
            
        Returns:
            ContractTemplate: Updated template instance
        """
        with transaction.atomic():
            contract_template = ContractTemplate.objects.get(template_id=template_id)
            
            # Update template data
            contract_template.template_data = template_data
            contract_template.name = template_data.get('title', contract_template.name)
            contract_template.description = template_data.get('description', contract_template.description)
            contract_template.status = 'PUBLISHED' if template_data.get('is_published') else 'DRAFT'
            contract_template.updated_at = timezone.now()
            
            contract_template.save()
            return contract_template
    
    @staticmethod
    def generate_contract_from_template(
        template_id: str, 
        opportunity_id: int = None,
        contract_data: dict = None,
        created_by: User = None
    ) -> Contract:
        """
        Generate a new contract from a template
        
        Args:
            template_id (str): ID of the template to use
            opportunity_id (int): Optional opportunity to link the contract to
            contract_data (dict): Additional contract data to override template data
            created_by (User): User creating the contract
            
        Returns:
            Contract: Generated contract instance
        """
        with transaction.atomic():
            # Get the template
            template = ContractTemplate.objects.get(template_id=template_id)
            
            # Generate unique contract number
            contract_number = ContractTemplateService._generate_contract_number()
            
            # Extract contract data from template
            template_metadata = template.template_data.get('metadata', {})
            form_data = template_metadata.get('contractData', {})
            
            # Create new contract
            contract = Contract(
                contract_template=template,
                template_version_used=template.version,
                contract_number=contract_number,
                title=f"Certification Contract - {form_data.get('clientName', 'Client')}",
                contract_type='CERTIFICATION',
                description=form_data.get('serviceScope', 'Certification services contract'),
                created_by=created_by
            )
            
            # Set opportunity if provided
            if opportunity_id:
                from .models import Opportunity
                contract.opportunity_id = opportunity_id
            
            # Map template form data to contract fields
            ContractTemplateService._map_template_data_to_contract(contract, form_data, contract_data)
            
            # Save the contract
            contract.save()
            
            return contract
    
    @staticmethod
    def _map_template_data_to_contract(contract: Contract, template_data: dict, override_data: dict = None):
        """
        Map template form data to contract model fields
        
        Args:
            contract (Contract): Contract instance to populate
            template_data (dict): Data from template form builder
            override_data (dict): Optional data to override template data
        """
        # Use override data if provided, otherwise use template data
        data = {**template_data, **(override_data or {})}
        
        # Client Information
        contract.client_organization = data.get('clientName', '')
        contract.client_address = data.get('clientAddress', '')
        contract.client_contact_person = data.get('clientContact', '')
        contract.client_email = data.get('clientEmail', 'contact@example.com')
        
        # Company Information
        contract.cb_name = data.get('companyName', 'AceQu International Limited')
        contract.cb_address = data.get('companyAddress', '168 City Road, Cardiff, Wales, CF24 3JE, United Kingdom')
        
        # Service Scope
        contract.scope_of_work = data.get('serviceScope', '')
        
        # Fee Structure
        contract.fee_per_standard_year_1 = float(data.get('initialCertificationCost', 1000))
        contract.fee_per_standard_year_2 = float(data.get('firstSurveillanceCost', 1000))
        contract.fee_per_standard_year_3 = float(data.get('secondSurveillanceCost', 1000))
        contract.recertification_fee = float(data.get('recertificationCost', 0)) if data.get('recertificationCost') else None
        
        # Calculate total contract value
        total_value = (
            contract.fee_per_standard_year_1 + 
            contract.fee_per_standard_year_2 + 
            contract.fee_per_standard_year_3
        )
        if contract.recertification_fee:
            total_value += contract.recertification_fee
        contract.contract_value = total_value
        
        # Contract Dates
        contract.agreement_date = ContractTemplateService._parse_date(data.get('contractDate'))
        contract.start_date = ContractTemplateService._parse_date(data.get('startDate')) or date.today()
        contract.end_date = ContractTemplateService._parse_date(data.get('endDate')) or date.today()
        
        # Default values
        contract.currency = 'USD'
        contract.status = 'DRAFT'
    
    @staticmethod
    def _parse_date(date_string: str) -> date:
        """
        Parse date string from various formats
        
        Args:
            date_string (str): Date string to parse
            
        Returns:
            date: Parsed date object or None
        """
        if not date_string:
            return None
            
        try:
            # Try ISO format first
            if 'T' in date_string:
                return datetime.fromisoformat(date_string.replace('Z', '+00:00')).date()
            else:
                return datetime.strptime(date_string, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _generate_contract_number() -> str:
        """
        Generate a unique contract number
        
        Returns:
            str: Unique contract number
        """
        # Get current year and count of contracts this year
        current_year = timezone.now().year
        yearly_count = Contract.objects.filter(
            contract_number__startswith=f"CNT-{current_year}"
        ).count() + 1
        
        return f"CNT-{current_year}-{yearly_count:04d}"
    
    @staticmethod
    def get_template_by_id(template_id: str) -> ContractTemplate:
        """
        Get contract template by ID
        
        Args:
            template_id (str): Template ID
            
        Returns:
            ContractTemplate: Template instance
        """
        return ContractTemplate.objects.get(template_id=template_id)
    
    @staticmethod
    def list_templates(template_type: str = None, is_active: bool = True) -> list:
        """
        List available contract templates
        
        Args:
            template_type (str): Optional filter by template type
            is_active (bool): Filter by active status
            
        Returns:
            list: List of template instances
        """
        queryset = ContractTemplate.objects.filter(is_active=is_active)
        
        if template_type:
            queryset = queryset.filter(template_type=template_type.upper())
            
        return list(queryset.order_by('-created_at'))
    
    @staticmethod
    def get_default_template(template_type: str) -> ContractTemplate:
        """
        Get default template for a specific type
        
        Args:
            template_type (str): Template type
            
        Returns:
            ContractTemplate: Default template or None
        """
        return ContractTemplate.objects.filter(
            template_type=template_type.upper(),
            is_default=True,
            is_active=True
        ).first()
    
    @staticmethod
    def export_template_to_json(template_id: str) -> dict:
        """
        Export template data as JSON for backup or sharing
        
        Args:
            template_id (str): Template ID to export
            
        Returns:
            dict: Complete template data
        """
        template = ContractTemplate.objects.get(template_id=template_id)
        
        return {
            'template_id': template.template_id,
            'name': template.name,
            'description': template.description,
            'template_type': template.template_type,
            'template_data': template.template_data,
            'version': template.version,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
        }
    
    @staticmethod
    def import_template_from_json(template_json: dict, created_by: User = None) -> ContractTemplate:
        """
        Import template from JSON data
        
        Args:
            template_json (dict): Template data to import
            created_by (User): User importing the template
            
        Returns:
            ContractTemplate: Imported template instance
        """
        # Generate new template ID to avoid conflicts
        template_json['template_data']['id'] = str(uuid.uuid4())
        
        return ContractTemplateService.create_contract_template(
            template_data=template_json['template_data'],
            created_by=created_by
        )