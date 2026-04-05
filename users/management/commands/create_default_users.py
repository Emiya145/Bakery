import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from inventory.models import Location


class Command(BaseCommand):
    help = (
        'Create or update admin, manager, and employee users. '
        'Password from --password or DEPLOY_USER_PASSWORD environment variable.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=None,
            help='Password for all three users (overrides DEPLOY_USER_PASSWORD)',
        )

    def handle(self, *args, **options):
        password = options['password'] or os.environ.get('DEPLOY_USER_PASSWORD')
        if not password:
            self.stderr.write(
                self.style.ERROR(
                    'Missing password: pass --password or set DEPLOY_USER_PASSWORD.'
                )
            )
            return

        User = get_user_model()
        main = Location.objects.order_by('pk').first()

        specs = [
            (
                'admin',
                'ADMIN',
                {
                    'email': 'admin@bakery.local',
                    'is_staff': True,
                    'is_superuser': True,
                },
            ),
            (
                'manager',
                'MANAGER',
                {
                    'email': 'manager@bakery.local',
                    'is_staff': True,
                },
            ),
            (
                'employee',
                'STAFF',
                {
                    'email': 'employee@bakery.local',
                    'is_staff': True,
                    'location': main,
                },
            ),
        ]

        for username, role, fields in specs:
            if fields.get('location') is None:
                fields = {k: v for k, v in fields.items() if k != 'location'}
            defaults = {**fields, 'role': role}
            user, created = User.objects.get_or_create(
                username=username,
                defaults=defaults,
            )
            user.role = role
            user.set_password(password)
            user.email = fields.get('email', user.email)
            user.is_staff = fields.get('is_staff', True)
            user.is_superuser = fields.get('is_superuser', False)
            loc = fields.get('location')
            if loc is not None:
                user.location = loc
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'{"Created" if created else "Updated"} {username} ({role})'
                )
            )
