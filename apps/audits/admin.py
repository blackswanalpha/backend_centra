from django.contrib import admin
from .models import ISOStandard, Audit, AuditFinding, AuditChecklist, ChecklistItem


@admin.register(ISOStandard)
class ISOStandardAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    ordering = ['code']


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ['audit_number', 'client', 'iso_standard', 'audit_type', 'status', 'planned_start_date', 'lead_auditor']
    list_filter = ['status', 'audit_type', 'iso_standard', 'planned_start_date']
    search_fields = ['audit_number', 'title', 'client__name']
    date_hierarchy = 'planned_start_date'
    ordering = ['-planned_start_date']
    filter_horizontal = ['auditors']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'iso_standard', 'audit_type', 'audit_number', 'title', 'description', 'scope')
        }),
        ('Schedule', {
            'fields': ('planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date')
        }),
        ('Assignment', {
            'fields': ('lead_auditor', 'auditors')
        }),
        ('Status & Results', {
            'fields': ('status', 'findings_count', 'major_findings', 'minor_findings', 'opportunities')
        }),
        ('Certificate Information', {
            'fields': ('certificate_number', 'certificate_issue_date', 'certificate_expiry_date'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = ['finding_number', 'audit', 'finding_type', 'status', 'clause_reference', 'target_date']
    list_filter = ['finding_type', 'status', 'created_at']
    search_fields = ['finding_number', 'description', 'clause_reference', 'audit__audit_number']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('audit', 'finding_number', 'finding_type', 'clause_reference')
        }),
        ('Finding Details', {
            'fields': ('description', 'evidence', 'requirement')
        }),
        ('Corrective Action', {
            'fields': ('correction', 'corrective_action', 'root_cause')
        }),
        ('Timeline & Status', {
            'fields': ('status', 'target_date', 'actual_closure_date', 'responsible_person', 'verified_by')
        }),
    )


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 1
    fields = ['clause_reference', 'item_type', 'question', 'guidance', 'order']


@admin.register(AuditChecklist)
class AuditChecklistAdmin(admin.ModelAdmin):
    list_display = ['title', 'iso_standard', 'is_template', 'created_by', 'created_at']
    list_filter = ['is_template', 'iso_standard', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    inlines = [ChecklistItemInline]
    
    readonly_fields = ['created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

