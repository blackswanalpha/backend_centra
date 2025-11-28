from rest_framework import serializers
from django.contrib.auth.models import User
from apps.tasks.models import Task, TaskComment, TaskAttachment, TaskTemplate
from apps.clients.models import Client


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for nested representations"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
        read_only_fields = ['id', 'username', 'email']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class TaskCommentSerializer(serializers.ModelSerializer):
    """Serializer for task comments"""
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_data = UserSerializer(source='author', read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'task', 'author', 'author_name', 'author_data', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for task attachments"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = TaskAttachment
        fields = ['id', 'task', 'file', 'file_name', 'file_size', 'uploaded_by', 'uploaded_by_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model"""
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    assigned_to_data = UserSerializer(source='assigned_to', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    created_by_data = UserSerializer(source='created_by', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'task_type', 'priority', 'status',
            'assigned_to', 'assigned_to_name', 'assigned_to_data',
            'created_by', 'created_by_name', 'created_by_data',
            'client', 'client_name', 'parent_task',
            'due_date', 'start_date', 'completed_date',
            'estimated_hours', 'actual_hours', 'tags', 'progress_percentage',
            'created_at', 'updated_at', 'comments', 'attachments', 'subtasks'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subtasks(self, obj):
        """Get subtasks recursively"""
        subtasks = obj.subtasks.all()
        return TaskSerializer(subtasks, many=True, context=self.context).data


class TaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for task lists"""
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    subtasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'task_type', 'priority', 'status',
            'assigned_to', 'assigned_to_name',
            'created_by', 'created_by_name',
            'client', 'client_name', 'parent_task',
            'due_date', 'start_date', 'completed_date',
            'estimated_hours', 'actual_hours', 'tags', 'progress_percentage',
            'created_at', 'updated_at', 'subtasks_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subtasks_count(self, obj):
        return obj.subtasks.count()


class TaskTemplateSerializer(serializers.ModelSerializer):
    """Serializer for task templates"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TaskTemplate
        fields = ['id', 'name', 'description', 'task_type', 'template_data', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']





# Import Workflow models
from apps.tasks.models import Workflow, WorkflowStep, WorkflowTemplate


# Workflow Serializers

class WorkflowStepSerializer(serializers.ModelSerializer):
    """Serializer for workflow steps"""
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    assigned_to_data = UserSerializer(source='assigned_to', read_only=True)

    class Meta:
        model = WorkflowStep
        fields = [
            'id', 'workflow', 'title', 'description', 'order', 'status',
            'assigned_to', 'assigned_to_name', 'assigned_to_data',
            'due_date', 'completed_at', 'depends_on',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowSerializer(serializers.ModelSerializer):
    """Serializer for Workflow model"""
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    assigned_to_data = UserSerializer(source='assigned_to', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    created_by_data = UserSerializer(source='created_by', read_only=True)
    approver_name = serializers.CharField(source='approver.username', read_only=True)
    approver_data = UserSerializer(source='approver', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    steps = WorkflowStepSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow
        fields = [
            'id', 'title', 'description', 'workflow_type', 'priority', 'status',
            'assigned_to', 'assigned_to_name', 'assigned_to_data',
            'created_by', 'created_by_name', 'created_by_data',
            'client', 'client_name', 'template', 'template_name',
            'due_date', 'start_date', 'completed_date', 'estimated_duration',
            'current_step', 'completion_rate',
            'approval_required', 'approver', 'approver_name', 'approver_data', 'approved_at',
            'tags', 'created_at', 'updated_at', 'steps'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for workflow lists"""
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'title', 'description', 'workflow_type', 'priority', 'status',
            'assigned_to', 'assigned_to_name',
            'created_by', 'created_by_name',
            'client', 'client_name',
            'due_date', 'start_date', 'completed_date', 'estimated_duration',
            'current_step', 'completion_rate',
            'approval_required', 'tags', 'created_at', 'updated_at', 'steps_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_steps_count(self, obj):
        return obj.steps.count()


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Serializer for workflow templates"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = ['id', 'name', 'description', 'workflow_type', 'template_data', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
