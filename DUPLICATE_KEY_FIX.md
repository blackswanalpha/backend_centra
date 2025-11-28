# Template Save Fix - Duplicate Key Constraint

## Issue Resolved
**Error**: `duplicate key value violates unique constraint "contract_templates_template_type_version_is_24c1ac77_uniq"`

**Root Cause**: Database has a unique constraint on `(template_type, version, is_default)`. All new templates were being created with version "1.0" (the default), causing duplicates.

## Solution Applied

Modified `backend_centra/apps/business_development/contract_template_service.py`:

### Before:
```python
contract_template = ContractTemplate.objects.create(
    template_id=template_id,
    name=template_data.get('title', 'Untitled Contract Template'),
    # ... other fields
    # version was using model default of "1.0"
)
```

### After:
```python
# Generate unique version string using timestamp
version_timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
unique_version = f"1.0.{version_timestamp}"

contract_template = ContractTemplate.objects.create(
    template_id=template_id,
    name=template_data.get('title', 'Untitled Contract Template'),
    # ... other fields
    version=unique_version,  # e.g., "1.0.20251128223800"
)
```

## How It Works

1. **Timestamp-Based Versioning**:
   - Each new template gets a version like: `1.0.20251128223800`
   - Format: `1.0.YYYYMMDDHHMMSS`
   - This ensures every template has a unique version

2. **Constraint Satisfaction**:
   - Database constraint: `(template_type, version, is_default)` must be unique
   - Now with unique versions, there will be no conflicts

3. **Version Examples**:
   - First template: `1.0.20251128223800`
   - Second template: `1.0.20251128223845`
   - Third template: `1.0.20251128224001`

## Testing the Fix

1. **Restart Django Server** (required for code changes):
   ```bash
   cd /home/mbugua/Documents/augment-projects/AssureHub/backend_centra
   # Press Ctrl+C to stop current server, then:
   python manage.py runserver
   ```

2. **Try Creating a Template**:
   - Go to `http://localhost:3000/template/builder`
   - Create a template
   - Click "Save" or "Publish"
   - Should now work without the duplicate key error!

3. **Verify in Database**:
   ```bash
   cd backend_centra
   python manage.py shell
   ```
   ```python
   from apps.business_development.models import ContractTemplate
   templates = ContractTemplate.objects.all()
   for t in templates:
       print(f"{t.name}: version={t.version}, type={t.template_type}")
   ```

## What This Means

- ✅ You can now create multiple templates of the same type
- ✅ Each template will have a unique version automatically
- ✅ No more "duplicate key" errors
- ✅ Versions are semantically meaningful (include creation timestamp)

## Version Management

The version format `1.0.YYYYMMDDHHMMSS` provides:
- **Major version**: 1
- **Minor version**: 0  
- **Unique identifier**: Timestamp of creation

If you later want to update templates to new major/minor versions, you can modify the service to:
- Increment versions (1.0 → 1.1 → 2.0)
- Track version history
- Support template version rollbacks

## Alternative Solutions (Not Implemented)

Other ways this could have been fixed:

1. **Make is_default=True for one template**: Would allow multiple templates with same type/version, but only one can be default
2. **Remove the constraint**: Would allow true duplicates (not recommended)
3. **Use UUID for version**: Would work but less human-readable
4. **Auto-increment version numbers**: More complex, requires tracking version counter per type

The timestamp-based approach was chosen because:
- Simple to implement
- Automatically unique
- Human-readable
- Sortable chronologically
- No additional database queries needed

## Next Steps

After restarting the Django server:
1. Clear any existing templates if needed (or keep them)
2. Create new templates - they should save successfully
3. Each template will have a unique version automatically
