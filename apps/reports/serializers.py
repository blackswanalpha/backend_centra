from rest_framework import serializers
from .models import ReportTemplate, GeneratedReport, Dashboard, DashboardWidget, ReportShare


class ReportTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'report_type', 'description', 'template_config',
            'is_public', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class ReportShareSerializer(serializers.ModelSerializer):
    shared_with_name = serializers.CharField(source='shared_with.username', read_only=True)
    shared_by_name = serializers.CharField(source='shared_by.username', read_only=True)
    
    class Meta:
        model = ReportShare
        fields = [
            'id', 'report', 'shared_with', 'shared_with_name', 'permission',
            'expires_at', 'is_active', 'last_accessed', 'access_count',
            'shared_by', 'shared_by_name', 'created_at'
        ]
        read_only_fields = ['shared_by', 'last_accessed', 'access_count', 'created_at']


class GeneratedReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    shares = ReportShareSerializer(many=True, read_only=True)
    
    class Meta:
        model = GeneratedReport
        fields = [
            'id', 'template', 'template_name', 'title', 'description', 'parameters',
            'start_date', 'end_date', 'status', 'report_file', 'file_format',
            'generated_by', 'generated_by_name', 'generation_time', 'error_message',
            'is_scheduled', 'schedule_frequency', 'next_run_date', 'created_at',
            'completed_at', 'shares'
        ]
        read_only_fields = [
            'generated_by', 'generation_time', 'created_at', 'completed_at', 'shares'
        ]


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'dashboard', 'title', 'widget_type', 'config', 'data_source',
            'position_x', 'position_y', 'width', 'height', 'refresh_interval',
            'last_updated', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_updated', 'created_at', 'updated_at']


class DashboardSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    widgets = DashboardWidgetSerializer(many=True, read_only=True)
    widget_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'description', 'layout_config', 'is_default', 'is_public',
            'owner', 'owner_name', 'created_at', 'updated_at', 'widgets', 'widget_count'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at', 'widgets']
    
    def get_widget_count(self, obj):
        return obj.widgets.filter(is_active=True).count()