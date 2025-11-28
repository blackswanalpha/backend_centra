import os
import django
import sys

# Set up Django environment
sys.path.append('/home/mbugua/Documents/augment-projects/AssureHub/backend_centra')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.job_pipeline.models import JobPipeline
from apps.business_development.models import Lead
from django.contrib.auth.models import User

def create_pipeline():
    # Get a user
    user = User.objects.first()
    if not user:
        print("No user found")
        return

    # Create a lead
    lead = Lead.objects.create(
        company_name="Test Company PL-00001",
        contact_person="John Doe",
        email="john@test.com",
        status="QUALIFIED",
        estimated_value=10000,
        currency="USD",
        assigned_to=user,
        created_by=user
    )
    print(f"Created Lead: {lead.id}")

    # Pipeline should be auto-created by signal
    pipeline = JobPipeline.objects.filter(lead=lead).first()
    if pipeline:
        print(f"Pipeline created: {pipeline.pipeline_id} (ID: {pipeline.id})")
        print(f"Number: {pipeline.number}")
        print(f"Current Stage: {pipeline.current_stage}")
    else:
        print("Pipeline NOT created by signal")

if __name__ == '__main__':
    create_pipeline()
