#!/usr/bin/env python
"""
Quick test script to verify certifications API is working.
Run this after starting the Django server.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.certifications.models import Certification, CertificateTemplate, CertificationHistory
from apps.clients.models import Client
from apps.audits.models import ISOStandard
from django.contrib.auth.models import User
from datetime import date, timedelta

def test_certifications():
    print("=" * 60)
    print("Testing Certifications System")
    print("=" * 60)
    
    # Check ISO Standards
    print("\n1. Checking ISO Standards...")
    standards = ISOStandard.objects.all()
    print(f"   Found {standards.count()} ISO standards")
    for std in standards[:3]:
        print(f"   - {std.code}: {std.name}")
    
    # Check Clients
    print("\n2. Checking Clients...")
    clients = Client.objects.all()
    print(f"   Found {clients.count()} clients")
    if clients.exists():
        print(f"   First client: {clients.first().name}")
    
    # Check Users
    print("\n3. Checking Users...")
    users = User.objects.all()
    print(f"   Found {users.count()} users")
    if users.exists():
        print(f"   First user: {users.first().username}")
    
    # Check Certificate Templates
    print("\n4. Checking Certificate Templates...")
    templates = CertificateTemplate.objects.all()
    print(f"   Found {templates.count()} templates")
    for template in templates:
        print(f"   - {template.name} ({template.template_type})")
    
    # Check Certifications
    print("\n5. Checking Certifications...")
    certifications = Certification.objects.all()
    print(f"   Found {certifications.count()} certifications")
    for cert in certifications:
        print(f"   - {cert.certificate_number}: {cert.client.name} - {cert.status}")
        print(f"     Days until expiry: {cert.days_until_expiry}")
    
    # Check Certification History
    print("\n6. Checking Certification History...")
    history = CertificationHistory.objects.all()
    print(f"   Found {history.count()} history entries")
    for entry in history[:5]:
        print(f"   - {entry.certification.certificate_number}: {entry.get_action_display()}")
    
    # Test creating a sample certification (if we have required data)
    if clients.exists() and standards.exists() and users.exists():
        print("\n7. Testing Certification Creation...")
        try:
            client = clients.first()
            standard = standards.first()
            user = users.first()
            
            # Check if test certification already exists
            test_cert_number = "TEST-CERT-001"
            if Certification.objects.filter(certificate_number=test_cert_number).exists():
                print(f"   Test certification {test_cert_number} already exists")
            else:
                cert = Certification.objects.create(
                    client=client,
                    iso_standard=standard,
                    certificate_number=test_cert_number,
                    issue_date=date.today(),
                    expiry_date=date.today() + timedelta(days=365*3),  # 3 years
                    status='active',
                    scope='Test certification scope',
                    lead_auditor=user,
                    certification_body='Test Certification Body',
                    accreditation_number='ACC-001',
                    created_by=user
                )
                print(f"   ✓ Created test certification: {cert.certificate_number}")
                print(f"   Status: {cert.status}")
                print(f"   Days until expiry: {cert.days_until_expiry}")
        except Exception as e:
            print(f"   ✗ Error creating test certification: {e}")
    else:
        print("\n7. Skipping certification creation (missing required data)")
        print(f"   Clients: {clients.count()}, Standards: {standards.count()}, Users: {users.count()}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == '__main__':
    test_certifications()

