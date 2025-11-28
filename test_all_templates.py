#!/usr/bin/env python
"""
Test script to verify certificate generation for all ISO standards.
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

def test_all_templates():
    print("=" * 80)
    print("Testing Certificate Generation for All ISO Standards")
    print("=" * 80)
    
    # Get test data
    client = Client.objects.first()
    user = User.objects.first()
    
    if not client or not user:
        print("ERROR: Missing required data (client or user)")
        return
    
    print(f"\nUsing client: {client.name}")
    print(f"Using user: {user.username}")
    
    # Get all active templates
    templates = CertificateTemplate.objects.filter(is_active=True).select_related('iso_standard')
    
    print(f"\nFound {templates.count()} active templates")
    print("\n" + "=" * 80)
    
    results = []
    
    for template in templates:
        print(f"\nTesting: {template.name}")
        print("-" * 80)
        
        iso_standard = template.iso_standard
        cert_number = f"TEST-{iso_standard.code.replace(':', '-').replace(' ', '-')}-001"
        
        try:
            # Create or get certification
            certification, created = Certification.objects.get_or_create(
                certificate_number=cert_number,
                defaults={
                    'client': client,
                    'iso_standard': iso_standard,
                    'issue_date': date.today(),
                    'expiry_date': date.today() + timedelta(days=365*3),
                    'status': 'active',
                    'scope': f'Implementation and maintenance of {iso_standard.name} for all organizational processes and activities.',
                    'lead_auditor': user,
                    'certification_body': 'AssureHub Certification Services',
                    'accreditation_number': 'ACC-2024-001',
                    'template': template,
                    'created_by': user
                }
            )
            
            if created:
                print(f"  ✓ Created certification: {cert_number}")
            else:
                print(f"  ✓ Using existing certification: {cert_number}")
                certification.template = template
                certification.save()
            
            # Generate certificate
            service = CertificateGenerationService(certification)
            output_path = service.generate(user=user)
            
            # Verify file
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"  ✓ Certificate generated successfully")
                print(f"  📄 File: {output_path}")
                print(f"  📊 Size: {file_size:,} bytes")
                
                results.append({
                    'iso_standard': iso_standard.code,
                    'template': template.name,
                    'status': 'SUCCESS',
                    'file_path': output_path,
                    'file_size': file_size
                })
            else:
                print(f"  ✗ File not found: {output_path}")
                results.append({
                    'iso_standard': iso_standard.code,
                    'template': template.name,
                    'status': 'FAILED',
                    'error': 'File not found'
                })
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'iso_standard': iso_standard.code if iso_standard else 'Unknown',
                'template': template.name,
                'status': 'ERROR',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    failed_count = sum(1 for r in results if r['status'] in ['FAILED', 'ERROR'])
    
    print(f"\nTotal Templates Tested: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    
    if success_count > 0:
        print("\n✅ Successful Generations:")
        for r in results:
            if r['status'] == 'SUCCESS':
                print(f"  - {r['iso_standard']}: {r['file_size']:,} bytes")
    
    if failed_count > 0:
        print("\n❌ Failed Generations:")
        for r in results:
            if r['status'] in ['FAILED', 'ERROR']:
                print(f"  - {r['iso_standard']}: {r.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)

if __name__ == '__main__':
    test_all_templates()

