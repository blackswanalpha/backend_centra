from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # Registration and verification
    path('register/', views.register, name='register'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    
    # Login and logout
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('me/', views.get_current_user, name='current_user'),
    
    # Password management
    path('password/reset/', views.password_reset_request, name='password_reset_request'),
    path('password/reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password/change/', views.change_password, name='change_password'),
    
    # Two-Factor Authentication
    path('2fa/enable/', views.enable_2fa, name='enable_2fa'),
    path('2fa/verify/', views.verify_2fa, name='verify_2fa'),
    path('2fa/disable/', views.disable_2fa, name='disable_2fa'),
]

