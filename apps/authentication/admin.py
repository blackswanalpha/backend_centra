from django.contrib import admin
from .models import (
    UserProfile, EmailVerificationCode, PasswordResetToken,
    TwoFactorBackupCode, LoginAttempt
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'department', 'email_verified', 'two_factor_enabled', 'created_at']
    list_filter = ['role', 'email_verified', 'two_factor_enabled', 'is_active']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'department']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'department', 'phone')
        }),
        ('Account Status', {
            'fields': ('is_active', 'email_verified', 'two_factor_enabled')
        }),
        ('Security', {
            'fields': ('two_factor_secret', 'last_login_ip')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'code']
    readonly_fields = ['created_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['created_at']


@admin.register(TwoFactorBackupCode)
class TwoFactorBackupCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'is_used', 'created_at', 'used_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'code']
    readonly_fields = ['created_at', 'used_at']


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'success', 'timestamp']
    list_filter = ['success', 'timestamp']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

