from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile, EmailVerificationCode, PasswordResetToken
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    VerifyEmailSerializer, ResendVerificationSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    ChangePasswordSerializer, Enable2FASerializer, Verify2FASerializer,
    Disable2FASerializer
)
from .utils import (
    send_verification_email, send_password_reset_email,
    generate_2fa_secret, verify_2fa_code, generate_backup_codes,
    verify_backup_code, get_client_ip, check_rate_limit, record_login_attempt
)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    Register a new user
    POST /api/v1/auth/register/
    """
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Create verification code
        verification_code = EmailVerificationCode.objects.create(user=user)
        
        # Send verification email
        send_verification_email(user, verification_code.code)
        
        return Response({
            'success': True,
            'message': 'Registration successful. Please check your email for verification code.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_email(request):
    """
    Verify email with code
    POST /api/v1/auth/verify-email/
    """
    serializer = VerifyEmailSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    code = serializer.validated_data['code']
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Find valid verification code
    try:
        verification = EmailVerificationCode.objects.get(
            user=user,
            code=code,
            is_used=False
        )
        
        if not verification.is_valid():
            return Response({
                'success': False,
                'error': 'Verification code has expired'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark code as used
        verification.is_used = True
        verification.save()
        
        # Activate user and mark email as verified
        user.is_active = True
        user.save()
        
        user.profile.email_verified = True
        user.profile.save()
        
        # Generate token
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'success': True,
            'message': 'Email verified successfully',
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
        
    except EmailVerificationCode.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid verification code'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_verification(request):
    """
    Resend verification code
    POST /api/v1/auth/resend-verification/
    """
    serializer = ResendVerificationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    
    try:
        user = User.objects.get(email=email)
        
        if user.profile.email_verified:
            return Response({
                'success': False,
                'error': 'Email already verified'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new verification code
        verification_code = EmailVerificationCode.objects.create(user=user)
        
        # Send verification email
        send_verification_email(user, verification_code.code)
        
        return Response({
            'success': True,
            'message': 'Verification code sent successfully'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """
    User login
    POST /api/v1/auth/login/
    """
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    two_factor_code = serializer.validated_data.get('two_factor_code', '')
    
    # Get client info
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Check rate limit
    if not check_rate_limit(username, ip_address):
        return Response({
            'success': False,
            'error': 'Too many failed login attempts. Please try again later.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Authenticate user
    # Check if username is an email
    if '@' in username:
        try:
            user_obj = User.objects.get(email=username)
            username = user_obj.username
        except User.DoesNotExist:
            pass

    user = authenticate(username=username, password=password)
    
    if user is None:
        # Record failed attempt
        record_login_attempt(username, ip_address, False, user_agent)
        
        return Response({
            'success': False,
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Check if email is verified
    if not user.profile.email_verified:
        return Response({
            'success': False,
            'error': 'Email not verified. Please verify your email first.',
            'requires_verification': True
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check 2FA
    if user.profile.two_factor_enabled:
        if not two_factor_code:
            return Response({
                'success': False,
                'error': '2FA code required',
                'requires_2fa': True
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Verify 2FA code or backup code
        is_valid = verify_2fa_code(user.profile.two_factor_secret, two_factor_code)
        
        if not is_valid:
            is_valid = verify_backup_code(user, two_factor_code)
        
        if not is_valid:
            record_login_attempt(username, ip_address, False, user_agent)
            return Response({
                'success': False,
                'error': 'Invalid 2FA code'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Record successful login
    record_login_attempt(username, ip_address, True, user_agent)
    
    # Update last login IP
    user.profile.last_login_ip = ip_address
    user.profile.save()
    
    # Generate or get token
    token, _ = Token.objects.get_or_create(user=user)
    
    return Response({
        'success': True,
        'token': token.key,
        'user': UserSerializer(user).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """
    User logout
    POST /api/v1/auth/logout/
    """
    try:
        # Delete the user's token
        request.user.auth_token.delete()
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Logout failed'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    """
    Get current user profile
    GET /api/v1/auth/me/
    """
    return Response({
        'success': True,
        'user': UserSerializer(request.user).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """
    Request password reset
    POST /api/v1/auth/password/reset/
    """
    serializer = PasswordResetRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']

    try:
        user = User.objects.get(email=email)

        # Create reset token
        reset_token = PasswordResetToken.objects.create(user=user)

        # Send reset email
        send_password_reset_email(user, reset_token.token)

        return Response({
            'success': True,
            'message': 'Password reset email sent'
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        # Don't reveal if email exists
        return Response({
            'success': True,
            'message': 'If the email exists, a password reset link has been sent'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """
    Confirm password reset with token
    POST /api/v1/auth/password/reset/confirm/
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    token = serializer.validated_data['token']
    new_password = serializer.validated_data['password']

    try:
        reset_token = PasswordResetToken.objects.get(token=token, is_used=False)

        if not reset_token.is_valid():
            return Response({
                'success': False,
                'error': 'Reset token has expired'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update password
        user = reset_token.user
        user.set_password(new_password)
        user.save()

        # Mark token as used
        reset_token.is_used = True
        reset_token.save()

        # Delete all tokens to force re-login
        Token.objects.filter(user=user).delete()

        return Response({
            'success': True,
            'message': 'Password reset successful'
        }, status=status.HTTP_200_OK)

    except PasswordResetToken.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid reset token'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """
    Change password for authenticated user
    POST /api/v1/auth/password/change/
    """
    serializer = ChangePasswordSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    old_password = serializer.validated_data['old_password']
    new_password = serializer.validated_data['new_password']

    # Check old password
    if not user.check_password(old_password):
        return Response({
            'success': False,
            'error': 'Current password is incorrect'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Update password
    user.set_password(new_password)
    user.save()

    # Delete all tokens to force re-login
    Token.objects.filter(user=user).delete()

    return Response({
        'success': True,
        'message': 'Password changed successfully. Please login again.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def enable_2fa(request):
    """
    Enable 2FA for user
    POST /api/v1/auth/2fa/enable/
    """
    serializer = Enable2FASerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    password = serializer.validated_data['password']

    # Verify password
    if not user.check_password(password):
        return Response({
            'success': False,
            'error': 'Invalid password'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Generate 2FA secret
    secret = generate_2fa_secret()

    # Save secret (not enabled yet until verified)
    user.profile.two_factor_secret = secret
    user.profile.save()

    # Generate QR code URL
    import pyotp
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name='AssureHub'
    )

    return Response({
        'success': True,
        'secret': secret,
        'qr_code_url': provisioning_uri,
        'message': 'Scan the QR code with your authenticator app and verify with a code'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_2fa(request):
    """
    Verify and activate 2FA
    POST /api/v1/auth/2fa/verify/
    """
    serializer = Verify2FASerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    code = serializer.validated_data['code']

    # Verify code
    if not verify_2fa_code(user.profile.two_factor_secret, code):
        return Response({
            'success': False,
            'error': 'Invalid 2FA code'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Enable 2FA
    user.profile.two_factor_enabled = True
    user.profile.save()

    # Generate backup codes
    backup_codes = generate_backup_codes(user)

    return Response({
        'success': True,
        'message': '2FA enabled successfully',
        'backup_codes': backup_codes
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def disable_2fa(request):
    """
    Disable 2FA for user
    POST /api/v1/auth/2fa/disable/
    """
    serializer = Disable2FASerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    password = serializer.validated_data['password']
    code = serializer.validated_data['code']

    # Verify password
    if not user.check_password(password):
        return Response({
            'success': False,
            'error': 'Invalid password'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Verify 2FA code
    if not verify_2fa_code(user.profile.two_factor_secret, code):
        return Response({
            'success': False,
            'error': 'Invalid 2FA code'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Disable 2FA
    user.profile.two_factor_enabled = False
    user.profile.two_factor_secret = ''
    user.profile.save()

    # Delete backup codes
    user.backup_codes.all().delete()

    return Response({
        'success': True,
        'message': '2FA disabled successfully'
    }, status=status.HTTP_200_OK)

