"""
Seed the database with a demo tenant, users, and source systems.
Usage: python manage.py seed_db
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.tenant.models import Tenant
from apps.sources.models import SourceSystem

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with demo data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Create demo tenant
        tenant, created = Tenant.objects.get_or_create(
            slug='demo-corp',
            defaults={
                'name': 'Demo Corporation',
                'contact_email': 'admin@democorp.com',
                'contact_name': 'Jane Smith',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created tenant: {tenant.name}'))
        else:
            self.stdout.write(f'Tenant exists: {tenant.name}')

        # Create admin user
        admin, created = User.objects.get_or_create(
            email='admin@democorp.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'tenant': tenant,
                'role': User.ROLE_ADMIN,
                'is_staff': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin: {admin.email} / password: admin123'))

        # Create analyst user
        analyst, created = User.objects.get_or_create(
            email='analyst@democorp.com',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Analyst',
                'tenant': tenant,
                'role': User.ROLE_ANALYST,
            }
        )
        if created:
            analyst.set_password('analyst123')
            analyst.save()
            self.stdout.write(self.style.SUCCESS(f'Created analyst: {analyst.email} / password: analyst123'))

        # Create reviewer user
        reviewer, created = User.objects.get_or_create(
            email='reviewer@democorp.com',
            defaults={
                'first_name': 'Bob',
                'last_name': 'Reviewer',
                'tenant': tenant,
                'role': User.ROLE_REVIEWER,
            }
        )
        if created:
            reviewer.set_password('reviewer123')
            reviewer.save()
            self.stdout.write(self.style.SUCCESS(f'Created reviewer: {reviewer.email} / password: reviewer123'))

        # Create source systems
        sources = [
            (SourceSystem.SOURCE_SAP, 'SAP Production'),
            (SourceSystem.SOURCE_UTILITY, 'Utility Portal East'),
            (SourceSystem.SOURCE_UTILITY, 'Utility Portal West'),
            (SourceSystem.SOURCE_TRAVEL, 'Concur Travel'),
        ]

        for source_type, name in sources:
            source, created = SourceSystem.objects.get_or_create(
                tenant=tenant,
                name=name,
                defaults={'source_type': source_type, 'is_active': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created source: {name}'))

        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write('  admin@democorp.com / admin123')
        self.stdout.write('  analyst@democorp.com / analyst123')
        self.stdout.write('  reviewer@democorp.com / reviewer123')
