from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.business_development.models import Lead, Opportunity, Contract
from apps.audits.models import Audit
from .models import JobPipeline, PipelineMilestone


@receiver(post_save, sender=Lead)
def create_pipeline_from_lead(sender, instance, created, **kwargs):
    """Auto-create pipeline when lead is created if conditions are met"""
    if created and instance.status in ['QUALIFIED', 'PROPOSAL_SENT']:
        # Check if pipeline doesn't already exist
        if not JobPipeline.objects.filter(lead=instance).exists():
            pipeline = JobPipeline.objects.create(
                client_name=instance.company_name,
                service_description=f"Lead for {instance.company_name}",
                estimated_value=instance.estimated_value,
                currency=instance.currency,
                current_stage='LEAD',
                lead=instance,
                owner=instance.assigned_to,
                lead_created_date=instance.created_at,
                created_by=instance.created_by
            )
            
            # Create initial milestones
            create_lead_milestones(pipeline, instance)


@receiver(post_save, sender=Opportunity)
def update_pipeline_from_opportunity(sender, instance, created, **kwargs):
    """Update or create pipeline when opportunity changes"""
    if created:
        # Try to find existing pipeline from lead
        pipeline = None
        if instance.lead:
            pipeline = JobPipeline.objects.filter(lead=instance.lead).first()
        
        if pipeline:
            # Update existing pipeline
            pipeline.opportunity = instance
            pipeline.current_stage = 'OPPORTUNITY'
            pipeline.opportunity_created_date = instance.created_at
            pipeline.client_name = instance.client.name if instance.client else pipeline.client_name
            pipeline.estimated_value = instance.estimated_value
            pipeline.currency = instance.currency
            pipeline.owner = instance.owner
            pipeline.save()
        else:
            # Create new pipeline
            pipeline = JobPipeline.objects.create(
                client_name=instance.client.name if instance.client else "Unknown Client",
                service_description=instance.description,
                estimated_value=instance.estimated_value,
                currency=instance.currency,
                current_stage='OPPORTUNITY',
                opportunity=instance,
                owner=instance.owner,
                opportunity_created_date=instance.created_at,
                created_by=instance.created_by
            )
        
        # Create opportunity milestones
        create_opportunity_milestones(pipeline, instance)
    
    else:
        # Update existing pipeline if status changed
        pipeline = JobPipeline.objects.filter(opportunity=instance).first()
        if pipeline:
            # Update pipeline based on opportunity status
            if instance.status == 'CLOSED_WON' and pipeline.current_stage == 'OPPORTUNITY':
                pipeline.current_stage = 'CONTRACT'
                pipeline.save()
            elif instance.status == 'CLOSED_LOST':
                pipeline.status = 'CANCELLED'
                pipeline.save()


@receiver(post_save, sender=Contract)
def update_pipeline_from_contract(sender, instance, created, **kwargs):
    """Update pipeline when contract is created or updated"""
    if created:
        # Find pipeline from opportunity
        pipeline = None
        if instance.opportunity:
            pipeline = JobPipeline.objects.filter(opportunity=instance.opportunity).first()
        
        if pipeline:
            # Update existing pipeline
            pipeline.contract = instance
            pipeline.current_stage = 'CONTRACT'
            pipeline.contract_signed_date = instance.agreement_date or timezone.now()
            pipeline.client_name = instance.client_organization
            pipeline.estimated_value = instance.contract_value
            pipeline.currency = instance.currency
            pipeline.save()
        else:
            # Create new pipeline
            pipeline = JobPipeline.objects.create(
                client_name=instance.client_organization,
                service_description=f"Contract services for {instance.client_organization}",
                estimated_value=instance.contract_value,
                currency=instance.currency,
                current_stage='CONTRACT',
                contract=instance,
                contract_signed_date=instance.agreement_date or timezone.now(),
                created_by=instance.created_by
            )
        
        # Create contract milestones
        create_contract_milestones(pipeline, instance)
    
    else:
        # Update existing pipeline
        pipeline = JobPipeline.objects.filter(contract=instance).first()
        if pipeline and instance.status == 'ACTIVE' and pipeline.current_stage != 'AUDIT_SCHEDULED':
            # Contract is now active, ready for audit scheduling
            pass


@receiver(post_save, sender=Audit)
def update_pipeline_from_audit(sender, instance, created, **kwargs):
    """Update pipeline when audit is created or updated"""
    if created and instance.pipeline:
        pipeline = instance.pipeline
        if pipeline.current_stage == 'CONTRACT':
            pipeline.current_stage = 'AUDIT_SCHEDULED'
            pipeline.audit_scheduled_date = timezone.now()
            pipeline.save()
            
            # Create audit milestones
            create_audit_milestones(pipeline, instance)
    
    elif not created:
        # Update pipeline based on audit status
        if instance.pipeline:
            pipeline = instance.pipeline
            if instance.status == 'IN_PROGRESS' and pipeline.current_stage == 'AUDIT_SCHEDULED':
                pipeline.current_stage = 'AUDIT_IN_PROGRESS'
                pipeline.save()
            elif instance.status == 'COMPLETED' and pipeline.current_stage == 'AUDIT_IN_PROGRESS':
                pipeline.current_stage = 'AUDIT_COMPLETED'
                pipeline.audit_completed_date = timezone.now()
                pipeline.save()


def create_lead_milestones(pipeline, lead):
    """Create initial milestones for lead stage"""
    milestones = [
        {
            'milestone_type': 'PROPOSAL_DUE',
            'title': 'Send Proposal',
            'description': f'Prepare and send proposal to {lead.company_name}',
            'due_date': (timezone.now().date() + timezone.timedelta(days=7)),
            'is_critical': True
        }
    ]
    
    for milestone_data in milestones:
        PipelineMilestone.objects.create(
            pipeline=pipeline,
            **milestone_data
        )


def create_opportunity_milestones(pipeline, opportunity):
    """Create milestones for opportunity stage"""
    milestones = [
        {
            'milestone_type': 'CONTRACT_SIGNATURE',
            'title': 'Contract Signature',
            'description': f'Get contract signed by {opportunity.client.name if opportunity.client else "client"}',
            'due_date': opportunity.expected_close_date,
            'is_critical': True
        }
    ]
    
    for milestone_data in milestones:
        PipelineMilestone.objects.create(
            pipeline=pipeline,
            **milestone_data
        )


def create_contract_milestones(pipeline, contract):
    """Create milestones for contract stage"""
    milestones = [
        {
            'milestone_type': 'AUDIT_SCHEDULED',
            'title': 'Schedule Initial Audit',
            'description': f'Schedule initial certification audit for {contract.client_organization}',
            'due_date': (contract.start_date + timezone.timedelta(days=30)) if contract.start_date else (timezone.now().date() + timezone.timedelta(days=30)),
            'is_critical': True
        }
    ]
    
    for milestone_data in milestones:
        PipelineMilestone.objects.create(
            pipeline=pipeline,
            **milestone_data
        )


def create_audit_milestones(pipeline, audit):
    """Create milestones for audit stages"""
    milestones = []
    
    # Audit start milestone
    if audit.planned_start_date:
        milestones.append({
            'milestone_type': 'AUDIT_START',
            'title': 'Audit Start',
            'description': f'Begin {audit.audit_type} audit',
            'due_date': audit.planned_start_date,
            'is_critical': True
        })
    
    # Audit completion milestone
    if audit.planned_end_date:
        milestones.append({
            'milestone_type': 'AUDIT_COMPLETION',
            'title': 'Audit Completion',
            'description': f'Complete {audit.audit_type} audit',
            'due_date': audit.planned_end_date,
            'is_critical': True
        })
        
        # Certificate issue milestone (2 weeks after audit completion)
        cert_date = audit.planned_end_date + timezone.timedelta(days=14)
        milestones.append({
            'milestone_type': 'CERTIFICATE_ISSUE',
            'title': 'Certificate Issue',
            'description': 'Issue certification after audit completion',
            'due_date': cert_date,
            'is_critical': True
        })
    
    for milestone_data in milestones:
        PipelineMilestone.objects.create(
            pipeline=pipeline,
            assigned_to=audit.lead_auditor,
            **milestone_data
        )