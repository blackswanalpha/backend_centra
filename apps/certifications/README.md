# Certifications Management System

## Overview
The Certifications app provides comprehensive management of client ISO certifications, including certificate generation, lifecycle tracking, and template management.

## Features

### Core Functionality
- ✅ Create, read, update, and delete certifications
- ✅ Track certification lifecycle (pending, active, expiring, expired, suspended, revoked)
- ✅ Automatic status updates based on expiry dates
- ✅ Certificate template management
- ✅ Certificate document generation from templates
- ✅ Complete audit trail with history tracking
- ✅ Certification renewal, suspension, and revocation
- ✅ Statistics and reporting

### Models

#### Certification
Main model for storing client certifications.

**Key Fields:**
- `certificate_number` - Unique certificate identifier
- `client` - Foreign key to Client
- `iso_standard` - Foreign key to ISOStandard
- `issue_date` - Certificate issue date
- `expiry_date` - Certificate expiry date
- `status` - Current status (pending, active, expiring-soon, expired, suspended, revoked)
- `scope` - Certification scope
- `lead_auditor` - Foreign key to User
- `template` - Foreign key to CertificateTemplate
- `document_url` - Generated certificate document

**Properties:**
- `days_until_expiry` - Days remaining until expiry
- `is_expired` - Boolean indicating if expired
- `is_expiring_soon` - Boolean indicating if expiring within 90 days

#### CertificateTemplate
Template management for certificate generation.

**Supported Template Types:**
- DOCX (Microsoft Word)
- HTML
- PDF
- JasperReports (.jrxml)

**Template Variables:**
Templates can use placeholders like `{{variable_name}}` which will be replaced with actual data:
- `{{certificate_number}}`, `{{issue_date}}`, `{{expiry_date}}`
- `{{client_name}}`, `{{client_address}}`, `{{client_email}}`
- `{{iso_standard_code}}`, `{{iso_standard_name}}`
- `{{lead_auditor_name}}`, `{{certification_body}}`
- And more...

#### CertificationHistory
Audit trail for all certification actions.

**Tracked Actions:**
- Created, Issued, Renewed, Suspended, Revoked, Expired, Reactivated, Updated, Document Generated

## API Endpoints

### Certifications

```
GET    /api/v1/certifications/                    - List all certifications
POST   /api/v1/certifications/                    - Create new certification
GET    /api/v1/certifications/{id}/               - Get certification details
PUT    /api/v1/certifications/{id}/               - Update certification
DELETE /api/v1/certifications/{id}/               - Delete certification
GET    /api/v1/certifications/statistics/         - Get statistics
GET    /api/v1/certifications/expiring/?days=90   - Get expiring certifications
POST   /api/v1/certifications/{id}/generate/      - Generate certificate document
POST   /api/v1/certifications/{id}/renew/         - Renew certification
POST   /api/v1/certifications/{id}/suspend/       - Suspend certification
POST   /api/v1/certifications/{id}/revoke/        - Revoke certification
POST   /api/v1/certifications/{id}/reactivate/    - Reactivate certification
```

### Certificate Templates

```
GET    /api/v1/certificate-templates/             - List all templates
POST   /api/v1/certificate-templates/             - Create new template
GET    /api/v1/certificate-templates/{id}/        - Get template details
PUT    /api/v1/certificate-templates/{id}/        - Update template
DELETE /api/v1/certificate-templates/{id}/        - Delete template
GET    /api/v1/certificate-templates/active/      - Get active templates
GET    /api/v1/certificate-templates/defaults/    - Get default templates
```

## Usage Examples

### Creating a Certification

```python
from apps.certifications.models import Certification
from apps.clients.models import Client
from apps.audits.models import ISOStandard
from datetime import date, timedelta

certification = Certification.objects.create(
    client=Client.objects.get(id=1),
    iso_standard=ISOStandard.objects.get(code='ISO 9001:2015'),
    certificate_number='CERT-2024-001',
    issue_date=date.today(),
    expiry_date=date.today() + timedelta(days=365*3),
    status='active',
    scope='Quality Management System',
    lead_auditor=user,
    certification_body='ABC Certification Body',
    accreditation_number='ACC-12345'
)
```

### Generating a Certificate

```python
from apps.certifications.services import CertificateGenerationService

service = CertificateGenerationService(certification)
output_path = service.generate()
print(f"Certificate generated: {output_path}")
```

### API Request Example (cURL)

```bash
# Get all certifications
curl -H "Authorization: Token YOUR_TOKEN" \
     http://localhost:8000/api/v1/certifications/

# Create certification
curl -X POST \
     -H "Authorization: Token YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "client": 1,
       "iso_standard": 1,
       "certificate_number": "CERT-2024-002",
       "issue_date": "2024-01-01",
       "expiry_date": "2027-01-01",
       "status": "active",
       "scope": "Quality Management System"
     }' \
     http://localhost:8000/api/v1/certifications/

# Generate certificate
curl -X POST \
     -H "Authorization: Token YOUR_TOKEN" \
     http://localhost:8000/api/v1/certifications/{id}/generate/
```

## Management Commands

### Populate ISO Standards

```bash
python manage.py populate_iso_standards
```

Populates the database with common ISO standards:
- ISO 9001:2015 - Quality Management Systems
- ISO 14001:2015 - Environmental Management Systems
- ISO 45001:2018 - Occupational Health and Safety
- ISO 27001:2013 - Information Security
- ISO 22000:2018 - Food Safety
- ISO 50001:2018 - Energy Management
- ISO 13485:2016 - Medical Devices

## Dependencies

- `python-docx==1.1.2` - For DOCX template processing

## Future Enhancements

- [ ] JasperReports integration for advanced PDF generation
- [ ] HTML to PDF conversion using WeasyPrint
- [ ] Digital signature support
- [ ] Automated email notifications for expiring certificates
- [ ] Bulk certificate generation
- [ ] Certificate verification portal
- [ ] QR code generation for certificates
- [ ] Multi-language certificate support

## Testing

Run the test script:
```bash
python test_certifications_api.py
```

## License

Part of the AssureHub system.

