from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PayrollViewSet, PayrollEarningViewSet, PayrollDeductionViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'payroll', PayrollViewSet, basename='payroll')
router.register(r'payroll-earnings', PayrollEarningViewSet, basename='payroll-earning')
router.register(r'payroll-deductions', PayrollDeductionViewSet, basename='payroll-deduction')

urlpatterns = [
    path('', include(router.urls)),
]

