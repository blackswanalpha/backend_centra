from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskViewSet, TaskCommentViewSet, TaskAttachmentViewSet, TaskTemplateViewSet,
    WorkflowViewSet, WorkflowStepViewSet, WorkflowTemplateViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'task-comments', TaskCommentViewSet, basename='task-comment')
router.register(r'task-attachments', TaskAttachmentViewSet, basename='task-attachment')
router.register(r'task-templates', TaskTemplateViewSet, basename='task-template')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'workflow-steps', WorkflowStepViewSet, basename='workflow-step')
router.register(r'workflow-templates', WorkflowTemplateViewSet, basename='workflow-template')

urlpatterns = [
    path('', include(router.urls)),
]

