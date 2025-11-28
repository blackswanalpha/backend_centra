# Generated migration for adding many-to-many relationship for audit templates

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audits', '0003_audit_audit_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='audit',
            name='audit_templates',
            field=models.ManyToManyField(blank=True, related_name='audits_multi', to='audits.auditchecklist'),
        ),
    ]

