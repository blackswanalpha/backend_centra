from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission check for Admin role"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.role == 'ADMIN'
        )


class IsAuditor(permissions.BasePermission):
    """Permission check for Auditor role"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.role in ['ADMIN', 'AUDITOR']
        )


class IsBusinessDevelopment(permissions.BasePermission):
    """Permission check for Business Development role"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.role in ['ADMIN', 'BUSINESS_DEV']
        )


class IsConsultant(permissions.BasePermission):
    """Permission check for Consultant role"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.role in ['ADMIN', 'CONSULTANT']
        )


class IsFinance(permissions.BasePermission):
    """Permission check for Finance role"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.role in ['ADMIN', 'FINANCE']
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission check for object owner or admin"""
    
    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if (hasattr(request.user, 'profile') and 
            request.user.profile.role == 'ADMIN'):
            return True
        
        # Check if user is the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin can do anything, others can only read"""
    
    def has_permission(self, request, view):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for admin
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.role == 'ADMIN'
        )

