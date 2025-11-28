import pyotp
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerificationCode, PasswordResetToken, TwoFactorBackupCode, LoginAttempt


def send_verification_email(user, code):
    """Send email verification code"""
    subject = 'Verify Your Email - AssureHub'
    message = f"""
    Hello {user.first_name or user.username},
    
    Thank you for registering with AssureHub!
    
    Your email verification code is: {code}
    
    This code will expire in 15 minutes.
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    AssureHub Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False


def send_password_reset_email(user, token):
    """Send password reset email"""
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    
    subject = 'Password Reset Request - AssureHub'
    message = f"""
    Hello {user.first_name or user.username},
    
    You requested to reset your password for AssureHub.
    
    Click the link below to reset your password:
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you didn't request a password reset, please ignore this email.
    
    Best regards,
    AssureHub Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False


def generate_2fa_secret():
    """Generate a new 2FA secret"""
    return pyotp.random_base32()


def verify_2fa_code(secret, code):
    """Verify a 2FA code"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(user, count=10):
    """Generate backup codes for 2FA recovery"""
    codes = []
    for _ in range(count):
        backup_code = TwoFactorBackupCode.objects.create(user=user)
        codes.append(backup_code.code)
    return codes


def verify_backup_code(user, code):
    """Verify and use a backup code"""
    try:
        backup_code = TwoFactorBackupCode.objects.get(
            user=user,
            code=code,
            is_used=False
        )
        backup_code.is_used = True
        backup_code.used_at = timezone.now()
        backup_code.save()
        return True
    except TwoFactorBackupCode.DoesNotExist:
        return False


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(username, ip_address, max_attempts=5, window_minutes=15):
    """Check if login attempts exceed rate limit"""
    cutoff_time = timezone.now() - timedelta(minutes=window_minutes)
    
    # Count failed attempts in the time window
    failed_attempts = LoginAttempt.objects.filter(
        username=username,
        ip_address=ip_address,
        success=False,
        timestamp__gte=cutoff_time
    ).count()
    
    return failed_attempts < max_attempts


def record_login_attempt(username, ip_address, success, user_agent=''):
    """Record a login attempt"""
    LoginAttempt.objects.create(
        username=username,
        ip_address=ip_address,
        success=success,
        user_agent=user_agent
    )


def cleanup_expired_codes():
    """Clean up expired verification codes and tokens"""
    now = timezone.now()
    
    # Delete expired verification codes
    EmailVerificationCode.objects.filter(expires_at__lt=now).delete()
    
    # Delete expired password reset tokens
    PasswordResetToken.objects.filter(expires_at__lt=now).delete()
    
    # Delete old login attempts (older than 30 days)
    cutoff = now - timedelta(days=30)
    LoginAttempt.objects.filter(timestamp__lt=cutoff).delete()

