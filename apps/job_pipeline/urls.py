from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobPipelineViewSet, PipelineMilestoneViewSet, PipelineStageTransitionViewSet

router = DefaultRouter()
router.register(r'pipelines', JobPipelineViewSet)
router.register(r'milestones', PipelineMilestoneViewSet)
router.register(r'transitions', PipelineStageTransitionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]