from django.contrib import admin
from .models import Certification, CertificateTemplate, CertificationHistory


class CertificationHistoryInline(admin.TabularInline):
    """Inline admin for certification history."""
    model = CertificationHistory
    extra = 0
    readonly_fields = ('action', 'previous_status', 'new_status', 'performed_by', 'timestamp', 'notes')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    """Admin interface for certificate templates."""
    list_display = ('name', 'template_type', 'iso_standard', 'is_active', 'is_default', 'created_at')
    list_filter = ('template_type', 'is_active', 'is_default', 'iso_standard')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'iso_standard')
        }),
        ('Template Configuration', {
            'fields': ('template_type', 'template_file', 'variables')
        }),
        ('Status', {
            'fields': ('is_active', 'is_default')
        }),
        ('Metadata', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    """Admin interface for certifications."""
    list_display = (
        'certificate_number',
        'client',
        'iso_standard',
        'status',
        'issue_date',
        'expiry_date',
        'days_until_expiry_display'
    )
    list_filter = ('status', 'iso_standard', 'issue_date', 'expiry_date')
    search_fields = ('certificate_number', 'client__name', 'scope', 'certification_body')
    readonly_fields = ('id', 'created_at', 'updated_at', 'created_by', 'days_until_expiry')
    inlines = [CertificationHistoryInline]

    fieldsets = (
        ('Core Information', {
            'fields': ('client', 'iso_standard', 'audit', 'certificate_number')
        }),
        ('Dates & Status', {
            'fields': ('issue_date', 'expiry_date', 'status')
        }),
        ('Scope & Details', {
            'fields': ('scope', 'lead_auditor')
        }),
        ('Certification Body', {
            'fields': ('certification_body', 'accreditation_number')
        }),
        ('Template & Document', {
            'fields': ('template', 'document_url')
        }),
        ('Additional Information', {
            'fields': ('metadata', 'notes'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at', 'days_until_expiry'),
            'classes': ('collapse',)
        }),
    )

    def days_until_expiry_display(self, obj):
        """Display days until expiry with color coding."""
        days = obj.days_until_expiry
        if days is None:
            return '-'
        if days < 0:
            return f'Expired ({abs(days)} days ago)'
        elif days <= 30:
            return f'{days} days (Critical)'
        elif days <= 90:
            return f'{days} days (Warning)'
        else:
            return f'{days} days'
    days_until_expiry_display.short_description = 'Days Until Expiry'

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CertificationHistory)
class CertificationHistoryAdmin(admin.ModelAdmin):
    """Admin interface for certification history."""
    list_display = ('certification', 'action', 'previous_status', 'new_status', 'performed_by', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('certification__certificate_number', 'notes')
    readonly_fields = ('certification', 'action', 'previous_status', 'new_status', 'performed_by', 'timestamp', 'notes', 'metadata')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
