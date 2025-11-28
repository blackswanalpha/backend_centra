#!/usr/bin/env python
"""
Script to create admin users for AssureHub
Usage: python create_admin.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from apps.authentication.models import UserProfile


def create_admin_user():
    """Create an admin user interactively"""
    
    print("=" * 60)
    print("AssureHub - Create Admin User")
    print("=" * 60)
    print()
    
    # Get user input
    username = input("Enter username: ").strip()
    if not username:
        print("❌ Username is required!")
        return
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"❌ User '{username}' already exists!")
        return
    
    email = input("Enter email: ").strip()
    if not email:
        print("❌ Email is required!")
        return
    
    # Check if email already exists
    if User.objects.filter(email=email).exists():
        print(f"❌ Email '{email}' already exists!")
        return
    
    first_name = input("Enter first name: ").strip()
    last_name = input("Enter last name: ").strip()
    
    password = input("Enter password (min 8 characters): ").strip()
    if len(password) < 8:
        print("❌ Password must be at least 8 characters!")
        return
    
    password_confirm = input("Confirm password: ").strip()
    if password != password_confirm:
        print("❌ Passwords do not match!")
        return
    
    department = input("Enter department (optional): ").strip()
    phone = input("Enter phone (optional): ").strip()
    
    # Ask for role
    print("\nAvailable roles:")
    print("1. ADMIN - Full system access")
    print("2. AUDITOR - Audit management")
    print("3. BUSINESS_DEV - Business development")
    print("4. CONSULTANT - Consulting projects")
    print("5. FINANCE - Financial data")
    print("6. EMPLOYEE - Basic access")
    
    role_choice = input("\nSelect role (1-6, default: 1): ").strip() or "1"
    
    role_map = {
        "1": "ADMIN",
        "2": "AUDITOR",
        "3": "BUSINESS_DEV",
        "4": "CONSULTANT",
        "5": "FINANCE",
        "6": "EMPLOYEE",
    }
    
    role = role_map.get(role_choice, "ADMIN")
    
    # Ask if user should be superuser
    is_superuser = role == "ADMIN"
    if role == "ADMIN":
        superuser_input = input("Make Django superuser? (Y/n): ").strip().lower()
        is_superuser = superuser_input != 'n'
    
    # Ask if email should be verified
    verify_email = input("Mark email as verified? (Y/n): ").strip().lower()
    email_verified = verify_email != 'n'
    
    print("\n" + "=" * 60)
    print("Creating user with the following details:")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"First Name: {first_name}")
    print(f"Last Name: {last_name}")
    print(f"Role: {role}")
    print(f"Department: {department or 'N/A'}")
    print(f"Phone: {phone or 'N/A'}")
    print(f"Superuser: {'Yes' if is_superuser else 'No'}")
    print(f"Email Verified: {'Yes' if email_verified else 'No'}")
    print("=" * 60)
    
    confirm = input("\nCreate this user? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("❌ User creation cancelled.")
        return
    
    try:
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_superuser,
            is_superuser=is_superuser
        )
        
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            role=role,
            department=department,
            phone=phone,
            email_verified=email_verified
        )
        
        print("\n" + "=" * 60)
        print("✅ User created successfully!")
        print("=" * 60)
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {profile.role}")
        print(f"Email Verified: {profile.email_verified}")
        print("\nYou can now login with these credentials.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error creating user: {str(e)}")


def main():
    """Main function"""
    try:
        create_admin_user()
    except KeyboardInterrupt:
        print("\n\n❌ User creation cancelled.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()

