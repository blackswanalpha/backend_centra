from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet, DepartmentViewSet, PositionViewSet, 
    EmployeeSkillViewSet, PerformanceReviewViewSet, TimeSheetViewSet
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'employee-skills', EmployeeSkillViewSet, basename='employeeskill')
router.register(r'performance-reviews', PerformanceReviewViewSet, basename='performancereview')
router.register(r'timesheets', TimeSheetViewSet, basename='timesheet')

urlpatterns = [
    path('', include(router.urls)),
]