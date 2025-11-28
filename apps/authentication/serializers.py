from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserProfile, EmailVerificationCode, PasswordResetToken


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = UserProfile
        fields = ['role', 'department', 'phone', 'avatar', 'email_verified', 
                  'two_factor_enabled', 'created_at', 'updated_at']
        read_only_fields = ['email_verified', 'two_factor_enabled', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user with profile"""
    
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'is_active', 'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined']


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration"""
    
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, default='EMPLOYEE')
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    def validate_username(self, value):
        """Check if username already exists"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate(self, data):
        """Validate password match and strength"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        
        # Validate password strength
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        return data
    
    def create(self, validated_data):
        """Create user and profile"""
        # Remove password_confirm and profile fields
        validated_data.pop('password_confirm')
        role = validated_data.pop('role', 'EMPLOYEE')
        department = validated_data.pop('department', '')
        phone = validated_data.pop('phone', '')
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=False  # Inactive until email verified
        )
        
        # Create profile
        UserProfile.objects.create(
            user=user,
            role=role,
            department=department,
            phone=phone
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    two_factor_code = serializers.CharField(max_length=6, required=False, allow_blank=True)


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer for email verification"""
    
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class ResendVerificationSerializer(serializers.Serializer):
    """Serializer for resending verification code"""
    
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, data):
        """Validate password match and strength"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        
        # Validate password strength
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, data):
        """Validate password match and strength"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        
        # Validate password strength
        try:
            validate_password(data['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return data


class Enable2FASerializer(serializers.Serializer):
    """Serializer for enabling 2FA"""
    
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class Verify2FASerializer(serializers.Serializer):
    """Serializer for verifying 2FA setup"""
    
    code = serializers.CharField(max_length=6)


class Disable2FASerializer(serializers.Serializer):
    """Serializer for disabling 2FA"""
    
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    code = serializers.CharField(max_length=6)

