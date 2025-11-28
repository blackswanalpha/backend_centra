# Generated migration to add fields from Excel spreadsheet
# This migration adds billing, physical location, and certification fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0003_alter_intakelink_options_and_more'),
    ]

    operations = [
        # Billing Information Fields
        migrations.AddField(
            model_name='client',
            name='currency_code',
            field=models.CharField(
                max_length=10,
                blank=True,
                null=True,
                choices=[
                    ('GBP', 'British Pound'),
                    ('USD', 'US Dollar'),
                    ('KES', 'Kenyan Shilling'),
                    ('EUR', 'Euro'),
                    ('TZS', 'Tanzanian Shilling'),
                    ('UGX', 'Ugandan Shilling'),
                ],
                help_text='Currency code for billing'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='billing_attention',
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text='Contact person for billing'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='billing_address',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Billing address line 1'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='billing_street2',
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text='Billing address line 2'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='billing_city',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text='Billing city'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='billing_state',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text='Billing state/province'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='billing_country',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text='Billing country'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='payment_terms',
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text='Payment terms (e.g., Due on Receipt, Net 30)'
            ),
        ),
        
        # Physical Location Fields
        migrations.AddField(
            model_name='client',
            name='physical_address',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Physical location address'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='city',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text='Physical city'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='country',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text='Physical country'
            ),
        ),
        
        # Project/Certification Fields
        migrations.AddField(
            model_name='client',
            name='project_ref',
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,
                help_text='Project reference number'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='scope_of_certification',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Detailed scope of certification'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='certificate_no',
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,
                help_text='Certificate number'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='registration_date',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='Initial registration date'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='certificate_date',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='Current certificate issue date'
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='expiry_date',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='Certificate expiry date'
            ),
        ),
    ]

