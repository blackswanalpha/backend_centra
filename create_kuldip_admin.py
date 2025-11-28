#!/usr/bin/env python
"""
Script to create admin user for Kuldip
Usage: python create_kuldip_admin.py
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


def create_kuldip_admin():
    """Create admin user for Kuldip"""
    
    print("=" * 60)
    print("AssureHub - Creating Admin User for Kuldip")
    print("=" * 60)
    print()
    
    # User details
    username = "kuldip"
    email = "kuldip@acequ.com"
    first_name = "Kuldip"
    last_name = ""
    password = "Kuldip@2024!"  # Secure password
    role = "ADMIN"
    department = "Administration"
    phone = ""
    is_superuser = True
    email_verified = True
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"❌ User '{username}' already exists!")
        existing_user = User.objects.get(username=username)
        print(f"   Email: {existing_user.email}")
        print(f"   Name: {existing_user.first_name} {existing_user.last_name}")
        
        # Check if it's the correct user
        if existing_user.email == email:
            print("✅ This appears to be the same user. Updating role to ADMIN...")
            try:
                # Get or create profile
                profile, created = UserProfile.objects.get_or_create(
                    user=existing_user,
                    defaults={
                        'role': role,
                        'department': department,
                        'phone': phone,
                        'email_verified': email_verified
                    }
                )
                
                if not created:
                    # Update existing profile
                    profile.role = role
                    profile.department = department
                    profile.email_verified = email_verified
                    profile.save()
                
                # Make sure user is superuser
                existing_user.is_staff = True
                existing_user.is_superuser = True
                existing_user.save()
                
                print("\n✅ User updated successfully!")
                print(f"Username: {existing_user.username}")
                print(f"Email: {existing_user.email}")
                print(f"Role: {profile.role}")
                print(f"Superuser: Yes")
                print(f"Email Verified: {profile.email_verified}")
                return
                
            except Exception as e:
                print(f"❌ Error updating user: {str(e)}")
                return
        else:
            print("❌ Username exists with different email. Please choose a different username.")
            return
    
    # Check if email already exists
    if User.objects.filter(email=email).exists():
        print(f"❌ Email '{email}' already exists with different username!")
        existing_user = User.objects.get(email=email)
        print(f"   Existing username: {existing_user.username}")
        return
    
    print("Creating user with the following details:")
    print("=" * 60)
    print(f"Username: {username}")
    print(f"Email: {email}")
    print(f"First Name: {first_name}")
    print(f"Last Name: {last_name}")
    print(f"Role: {role}")
    print(f"Department: {department}")
    print(f"Superuser: {'Yes' if is_superuser else 'No'}")
    print(f"Email Verified: {'Yes' if email_verified else 'No'}")
    print("=" * 60)
    
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
        print(f"Password: {password}")
        print(f"Role: {profile.role}")
        print(f"Superuser: Yes")
        print(f"Email Verified: {profile.email_verified}")
        print("\nKuldip can now login with these credentials:")
        print(f"- Frontend: http://localhost:3000/auth/login")
        print(f"- Django Admin: http://localhost:8000/admin/")
        print("=" * 60)
        
        return {
            'username': user.username,
            'email': user.email,
            'password': password,
            'role': profile.role,
            'superuser': True,
            'email_verified': profile.email_verified
        }
        
    except Exception as e:
        print(f"\n❌ Error creating user: {str(e)}")
        return None


def main():
    """Main function"""
    try:
        result = create_kuldip_admin()
        if result:
            print(f"\n🎉 Admin user for Kuldip created successfully!")
    except KeyboardInterrupt:
        print("\n\n❌ User creation cancelled.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()