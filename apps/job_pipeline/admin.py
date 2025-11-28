from django.contrib import admin
from .models import JobPipeline, PipelineStageTransition, PipelineMilestone


@admin.register(JobPipeline)
class JobPipelineAdmin(admin.ModelAdmin):
    list_display = [
        'pipeline_id', 'client_name', 'current_stage', 'status', 
        'estimated_value', 'currency', 'owner', 'created_at'
    ]
    list_filter = ['current_stage', 'status', 'currency', 'created_at']
    search_fields = ['pipeline_id', 'client_name', 'service_description']
    readonly_fields = ['pipeline_id', 'created_at', 'updated_at', 'stage_progress_percentage', 'days_in_current_stage']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pipeline_id', 'client_name', 'service_description', 'estimated_value', 'currency')
        }),
        ('Stage & Status', {
            'fields': ('current_stage', 'status', 'stage_progress_percentage', 'days_in_current_stage')
        }),
        ('Related Objects', {
            'fields': ('lead', 'opportunity', 'contract')
        }),
        ('Timeline', {
            'fields': (
                'lead_created_date', 'opportunity_created_date', 'contract_signed_date',
                'audit_scheduled_date', 'audit_completed_date', 'certificate_issued_date'
            )
        }),
        ('Milestones', {
            'fields': ('next_milestone', 'next_milestone_date')
        }),
        ('Assignment', {
            'fields': ('owner', 'created_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PipelineStageTransition)
class PipelineStageTransitionAdmin(admin.ModelAdmin):
    list_display = ['pipeline', 'from_stage', 'to_stage', 'transitioned_at', 'transitioned_by']
    list_filter = ['from_stage', 'to_stage', 'transitioned_at']
    search_fields = ['pipeline__pipeline_id', 'pipeline__client_name']
    readonly_fields = ['transitioned_at']
    
    fieldsets = (
        ('Transition Details', {
            'fields': ('pipeline', 'from_stage', 'to_stage', 'notes')
        }),
        ('Metadata', {
            'fields': ('transitioned_at', 'transitioned_by')
        }),
    )


@admin.register(PipelineMilestone)
class PipelineMilestoneAdmin(admin.ModelAdmin):
    list_display = [
        'pipeline', 'title', 'milestone_type', 'due_date', 
        'is_completed', 'is_critical', 'assigned_to'
    ]
    list_filter = ['milestone_type', 'is_completed', 'is_critical', 'due_date']
    search_fields = ['pipeline__pipeline_id', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at', 'is_overdue', 'days_remaining']
    
    fieldsets = (
        ('Milestone Details', {
            'fields': ('pipeline', 'milestone_type', 'title', 'description')
        }),
        ('Timeline', {
            'fields': ('due_date', 'completed_date', 'is_completed', 'is_overdue', 'days_remaining')
        }),
        ('Priority & Assignment', {
            'fields': ('is_critical', 'assigned_to')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pipeline', 'assigned_to')