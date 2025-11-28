from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from apps.tasks.models import Task, TaskComment, TaskAttachment, TaskTemplate, Workflow, WorkflowStep, WorkflowTemplate
from .serializers import (
    TaskSerializer, TaskListSerializer, TaskCommentSerializer,
    TaskAttachmentSerializer, TaskTemplateSerializer,
    WorkflowSerializer, WorkflowListSerializer, WorkflowStepSerializer, WorkflowTemplateSerializer
)


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Task model with CRUD operations.
    Supports filtering, searching, and ordering.

    Endpoints:
    - GET /api/v1/tasks/ - List all tasks
    - POST /api/v1/tasks/ - Create new task
    - GET /api/v1/tasks/{id}/ - Get task details
    - PUT /api/v1/tasks/{id}/ - Update task
    - DELETE /api/v1/tasks/{id}/ - Delete task
    - GET /api/v1/tasks/stats/ - Get task statistics
    """
    queryset = Task.objects.select_related(
        'assigned_to', 'created_by', 'client', 'parent_task'
    ).prefetch_related('comments', 'attachments', 'subtasks')
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'task_type', 'assigned_to', 'client', 'parent_task']
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['title', 'created_at', 'due_date', 'priority', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return TaskListSerializer
        return TaskSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by assigned user
        assigned_to = self.request.query_params.get('assigned_to', None)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(due_date__lte=end_date)

        # Filter out subtasks if requested (only show parent tasks)
        only_parents = self.request.query_params.get('only_parents', None)
        if only_parents == 'true':
            queryset = queryset.filter(parent_task__isnull=True)

        return queryset

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get task statistics"""
        queryset = self.get_queryset()

        total = queryset.count()
        by_status = {
            'todo': queryset.filter(status='TODO').count(),
            'in_progress': queryset.filter(status='IN_PROGRESS').count(),
            'in_review': queryset.filter(status='IN_REVIEW').count(),
            'completed': queryset.filter(status='COMPLETED').count(),
            'cancelled': queryset.filter(status='CANCELLED').count(),
            'on_hold': queryset.filter(status='ON_HOLD').count(),
        }
        by_priority = {
            'low': queryset.filter(priority='LOW').count(),
            'medium': queryset.filter(priority='MEDIUM').count(),
            'high': queryset.filter(priority='HIGH').count(),
            'critical': queryset.filter(priority='CRITICAL').count(),
        }
        overdue = queryset.filter(
            due_date__lt=timezone.now(),
            status__in=['TODO', 'IN_PROGRESS', 'IN_REVIEW']
        ).count()

        return Response({
            'success': True,
            'data': {
                'total': total,
                'by_status': by_status,
                'by_priority': by_priority,
                'overdue': overdue,
            }
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark task as completed"""
        task = self.get_object()
        task.status = 'COMPLETED'
        task.completed_date = timezone.now()
        task.progress_percentage = 100
        task.save()

        serializer = self.get_serializer(task)
        return Response(serializer.data)


class TaskCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for task comments"""
    queryset = TaskComment.objects.select_related('task', 'author').all()
    serializer_class = TaskCommentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task']
    ordering = ['created_at']

    def perform_create(self, serializer):
        """Set author to current user"""
        serializer.save(author=self.request.user if self.request.user.is_authenticated else None)


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    """ViewSet for task attachments"""
    queryset = TaskAttachment.objects.select_related('task', 'uploaded_by').all()
    serializer_class = TaskAttachmentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """Set uploaded_by to current user"""
        serializer.save(uploaded_by=self.request.user if self.request.user.is_authenticated else None)





class TaskTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for task templates"""
    queryset = TaskTemplate.objects.select_related('created_by').all()
    serializer_class = TaskTemplateSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task_type']
    search_fields = ['name', 'description']
    ordering = ['name']

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)




# Workflow ViewSets

class WorkflowViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Workflow model with CRUD operations.
    Supports filtering, searching, and ordering.

    Endpoints:
    - GET /api/v1/workflows/ - List all workflows
    - POST /api/v1/workflows/ - Create new workflow
    - GET /api/v1/workflows/{id}/ - Get workflow details
    - PUT /api/v1/workflows/{id}/ - Update workflow
    - DELETE /api/v1/workflows/{id}/ - Delete workflow
    - GET /api/v1/workflows/stats/ - Get workflow statistics
    """
    queryset = Workflow.objects.select_related(
        'assigned_to', 'created_by', 'client', 'template', 'approver'
    ).prefetch_related('steps')
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'workflow_type', 'assigned_to', 'client', 'approval_required']
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['title', 'created_at', 'due_date', 'priority', 'status', 'completion_rate']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by assigned user
        assigned_to = self.request.query_params.get('assigned_to', None)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(due_date__lte=end_date)

        return queryset

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get workflow statistics"""
        queryset = self.get_queryset()

        total = queryset.count()
        by_status = {
            'not_started': queryset.filter(status='NOT_STARTED').count(),
            'in_progress': queryset.filter(status='IN_PROGRESS').count(),
            'completed': queryset.filter(status='COMPLETED').count(),
            'cancelled': queryset.filter(status='CANCELLED').count(),
            'on_hold': queryset.filter(status='ON_HOLD').count(),
        }
        by_priority = {
            'low': queryset.filter(priority='LOW').count(),
            'medium': queryset.filter(priority='MEDIUM').count(),
            'high': queryset.filter(priority='HIGH').count(),
            'critical': queryset.filter(priority='CRITICAL').count(),
        }
        overdue = queryset.filter(
            due_date__lt=timezone.now(),
            status__in=['NOT_STARTED', 'IN_PROGRESS']
        ).count()

        return Response({
            'success': True,
            'data': {
                'total': total,
                'by_status': by_status,
                'by_priority': by_priority,
                'overdue': overdue,
            }
        })

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark workflow as completed"""
        workflow = self.get_object()
        workflow.status = 'COMPLETED'
        workflow.completed_date = timezone.now()
        workflow.completion_rate = 100
        workflow.save()

        serializer = self.get_serializer(workflow)
        return Response(serializer.data)


class WorkflowStepViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow steps"""
    queryset = WorkflowStep.objects.select_related('workflow', 'assigned_to').all()
    serializer_class = WorkflowStepSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['workflow', 'status', 'assigned_to']
    ordering = ['workflow', 'order']

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark step as completed"""
        step = self.get_object()
        step.status = 'COMPLETED'
        step.completed_at = timezone.now()
        step.save()

        # Update workflow progress
        workflow = step.workflow
        total_steps = workflow.steps.count()
        completed_steps = workflow.steps.filter(status='COMPLETED').count()
        workflow.completion_rate = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        workflow.save()

        serializer = self.get_serializer(step)
        return Response(serializer.data)


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow templates"""
    queryset = WorkflowTemplate.objects.select_related('created_by').all()
    serializer_class = WorkflowTemplateSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['workflow_type']
    search_fields = ['name', 'description']
    ordering = ['name']

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
