from django.core.management.base import BaseCommand
from apps.audits.models import ISOStandard


class Command(BaseCommand):
    help = 'Populate database with common ISO standards'

    def handle(self, *args, **options):
        standards = [
            {
                'code': 'ISO 9001:2015',
                'name': 'Quality Management Systems',
                'description': 'ISO 9001:2015 specifies requirements for a quality management system when an organization needs to demonstrate its ability to consistently provide products and services that meet customer and applicable statutory and regulatory requirements.'
            },
            {
                'code': 'ISO 14001:2015',
                'name': 'Environmental Management Systems',
                'description': 'ISO 14001:2015 specifies the requirements for an environmental management system that an organization can use to enhance its environmental performance.'
            },
            {
                'code': 'ISO 45001:2018',
                'name': 'Occupational Health and Safety Management Systems',
                'description': 'ISO 45001:2018 specifies requirements for an occupational health and safety (OH&S) management system, and gives guidance for its use, to enable organizations to provide safe and healthy workplaces.'
            },
            {
                'code': 'ISO 27001:2013',
                'name': 'Information Security Management Systems',
                'description': 'ISO 27001:2013 specifies the requirements for establishing, implementing, maintaining and continually improving an information security management system within the context of the organization.'
            },
            {
                'code': 'ISO 22000:2018',
                'name': 'Food Safety Management Systems',
                'description': 'ISO 22000:2018 specifies requirements for a food safety management system to enable an organization that is in the food chain to demonstrate its ability to control food safety hazards.'
            },
            {
                'code': 'ISO 50001:2018',
                'name': 'Energy Management Systems',
                'description': 'ISO 50001:2018 specifies requirements for establishing, implementing, maintaining and improving an energy management system.'
            },
            {
                'code': 'ISO 13485:2016',
                'name': 'Medical Devices - Quality Management Systems',
                'description': 'ISO 13485:2016 specifies requirements for a quality management system where an organization needs to demonstrate its ability to provide medical devices and related services that consistently meet customer and applicable regulatory requirements.'
            },
            {
                'code': 'ISO 22301:2019',
                'name': 'Business Continuity Management Systems',
                'description': 'ISO 22301:2019 specifies requirements to plan, establish, implement, operate, monitor, review, maintain and continually improve a documented management system to protect against, reduce the likelihood of occurrence, prepare for, respond to, and recover from disruptive incidents when they arise.'
            },
        ]

        created_count = 0
        updated_count = 0

        for standard_data in standards:
            standard, created = ISOStandard.objects.update_or_create(
                code=standard_data['code'],
                defaults={
                    'name': standard_data['name'],
                    'description': standard_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {standard.code} - {standard.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated: {standard.code} - {standard.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created: {created_count}, Updated: {updated_count}'
            )
        )

