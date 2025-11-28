#!/usr/bin/env python
"""
Test script to verify certificate generation with templates.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.certifications.models import Certification, CertificateTemplate
from apps.certifications.services import CertificateGenerationService
from apps.clients.models import Client
from apps.audits.models import ISOStandard
from django.contrib.auth.models import User
from datetime import date, timedelta

def test_certificate_generation():
    print("=" * 60)
    print("Testing Certificate Generation")
    print("=" * 60)
    
    # Get or create test data
    print("\n1. Checking test data...")
    
    # Get client
    client = Client.objects.first()
    if not client:
        print("  ✗ No clients found. Please create a client first.")
        return
    print(f"  ✓ Using client: {client.name}")
    
    # Get ISO standard
    iso_standard = ISOStandard.objects.filter(code='ISO 9001:2015').first()
    if not iso_standard:
        print("  ✗ ISO 9001:2015 not found. Please run populate_iso_standards.")
        return
    print(f"  ✓ Using ISO standard: {iso_standard.code}")
    
    # Get user
    user = User.objects.first()
    if not user:
        print("  ✗ No users found. Please create a user first.")
        return
    print(f"  ✓ Using user: {user.username}")
    
    # Get template
    template = CertificateTemplate.objects.filter(
        iso_standard=iso_standard,
        is_active=True
    ).first()
    if not template:
        print("  ✗ No template found. Please run load_certificate_templates.")
        return
    print(f"  ✓ Using template: {template.name}")
    
    # Create or get test certification
    print("\n2. Creating test certification...")
    cert_number = "TEST-CERT-GEN-001"
    
    certification, created = Certification.objects.get_or_create(
        certificate_number=cert_number,
        defaults={
            'client': client,
            'iso_standard': iso_standard,
            'issue_date': date.today(),
            'expiry_date': date.today() + timedelta(days=365*3),
            'status': 'active',
            'scope': 'Design, development, and manufacturing of quality management systems for industrial applications.',
            'lead_auditor': user,
            'certification_body': 'AssureHub Certification Services',
            'accreditation_number': 'ACC-2024-001',
            'template': template,
            'created_by': user
        }
    )
    
    if created:
        print(f"  ✓ Created new certification: {cert_number}")
    else:
        print(f"  ✓ Using existing certification: {cert_number}")
        # Update template
        certification.template = template
        certification.save()
    
    # Generate certificate
    print("\n3. Generating certificate document...")
    try:
        service = CertificateGenerationService(certification)
        output_path = service.generate(user=user)
        print(f"  ✓ Certificate generated successfully!")
        print(f"  📄 File: {output_path}")
        
        # Check if file exists
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"  📊 Size: {file_size:,} bytes")
        else:
            print(f"  ⚠ Warning: File not found at {output_path}")
        
        # Refresh certification from database
        certification.refresh_from_db()
        if certification.document_url:
            print(f"  ✓ Document URL saved: {certification.document_url}")
        
    except Exception as e:
        print(f"  ✗ Error generating certificate: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check history
    print("\n4. Checking certification history...")
    history_count = certification.history.count()
    print(f"  ✓ Found {history_count} history entries")
    
    for entry in certification.history.all()[:5]:
        print(f"    - {entry.get_action_display()} by {entry.performed_by.username if entry.performed_by else 'System'} at {entry.timestamp}")
    
    print("\n" + "=" * 60)
    print("Certificate Generation Test Complete!")
    print("=" * 60)
    print(f"\nYou can view the generated certificate at:")
    print(f"  {output_path}")

if __name__ == '__main__':
    test_certificate_generation()

