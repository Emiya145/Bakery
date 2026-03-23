from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import Ingredient, Location, Stock, StockMovement


class Command(BaseCommand):
    help = 'Seed sample data for local development/demo (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Do not create demo users',
        )
        parser.add_argument(
            '--password',
            default='demo12345',
            help='Password to use for demo users if they are created',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()

        main_location, _ = Location.objects.get_or_create(
            name='Main Bakery',
            defaults={'address': '123 Baker St', 'phone': '555-0100', 'is_active': True},
        )
        branch_location, _ = Location.objects.get_or_create(
            name='Downtown Branch',
            defaults={'address': '45 Market Ave', 'phone': '555-0110', 'is_active': True},
        )

        seed_user = None
        if not options['skip_users']:
            seed_user = self._ensure_demo_users(
                password=options['password'],
                main_location=main_location,
            )

        if seed_user is None:
            # If users are skipped, try to use any existing superuser/staff.
            User = get_user_model()
            seed_user = (
                User.objects.filter(is_superuser=True).first()
                or User.objects.filter(is_staff=True).first()
                or User.objects.first()
            )

        if seed_user is None:
            self.stdout.write(
                self.style.ERROR(
                    'No user exists to attribute StockMovement records to. Create a user first or run without --skip-users.'
                )
            )
            return

        ingredients = self._ensure_ingredients()

        # Create stock batches (some low, expiring soon, and expired)
        stock_plan = [
            # Main Bakery
            {
                'location': main_location,
                'rows': [
                    ('Flour', 'F-1001', today + timedelta(days=30), Decimal('25.00')),
                    ('Flour', 'F-1002', today + timedelta(days=5), Decimal('2.00')),
                    ('Sugar', 'S-2001', today + timedelta(days=180), Decimal('8.00')),
                    ('Butter', 'B-3001', today + timedelta(days=2), Decimal('1.00')),
                    ('Butter', 'B-2999', today - timedelta(days=2), Decimal('0.50')),
                    ('Eggs', 'E-4001', today + timedelta(days=10), Decimal('72.00')),
                    ('Milk', 'M-5001', today + timedelta(days=6), Decimal('12.00')),
                    ('Yeast', 'Y-6001', None, Decimal('1.50')),
                    ('Chocolate', 'C-7001', today + timedelta(days=90), Decimal('6.00')),
                    ('Vanilla Extract', 'V-8001', None, Decimal('0.80')),
                ],
            },
            # Downtown Branch
            {
                'location': branch_location,
                'rows': [
                    ('Flour', 'F-1101', today + timedelta(days=25), Decimal('3.00')),
                    ('Sugar', 'S-2101', today + timedelta(days=150), Decimal('2.00')),
                    ('Butter', 'B-3101', today + timedelta(days=1), Decimal('0.60')),
                    ('Eggs', 'E-4101', today + timedelta(days=8), Decimal('18.00')),
                    ('Milk', 'M-5101', today + timedelta(days=4), Decimal('2.00')),
                ],
            },
        ]

        created_stocks = 0
        updated_stocks = 0

        for plan in stock_plan:
            location = plan['location']
            for ingredient_name, batch_number, expiration_date, target_qty in plan['rows']:
                ingredient = ingredients[ingredient_name]

                stock, created = Stock.objects.get_or_create(
                    ingredient=ingredient,
                    location=location,
                    batch_number=batch_number,
                    defaults={
                        'quantity': Decimal('0.00'),
                        'expiration_date': expiration_date,
                    },
                )

                # Keep expiration date synced with seed plan.
                if stock.expiration_date != expiration_date:
                    stock.expiration_date = expiration_date
                    stock.save(update_fields=['expiration_date'])

                if created:
                    stock.quantity = target_qty
                    stock.save(update_fields=['quantity'])

                    StockMovement.objects.create(
                        stock=stock,
                        movement_type='IN',
                        quantity=target_qty,
                        quantity_before=Decimal('0.00'),
                        quantity_after=target_qty,
                        reason='Seed initial stock',
                        reference='SEED',
                        created_by=seed_user,
                    )
                    created_stocks += 1
                else:
                    if stock.quantity != target_qty:
                        quantity_before = stock.quantity
                        stock.quantity = target_qty
                        stock.save(update_fields=['quantity'])

                        StockMovement.objects.create(
                            stock=stock,
                            movement_type='ADJUSTMENT',
                            quantity=abs(target_qty - quantity_before),
                            quantity_before=quantity_before,
                            quantity_after=target_qty,
                            reason='Seed stock sync',
                            reference='SEED-SYNC',
                            created_by=seed_user,
                        )
                        updated_stocks += 1

        self.stdout.write(self.style.SUCCESS('Sample data seeded.'))
        self.stdout.write(f'Locations: {Location.objects.count()}')
        self.stdout.write(f'Ingredients: {Ingredient.objects.count()}')
        self.stdout.write(f'Stock batches created: {created_stocks}, updated: {updated_stocks}')
        self.stdout.write(f'Stock movements: {StockMovement.objects.filter(reference__startswith="SEED").count()}')

        if not options['skip_users']:
            self.stdout.write('Demo users (created if missing):')
            self.stdout.write('  - admin_demo / (password you passed via --password)')
            self.stdout.write('  - manager_demo / (password you passed via --password)')
            self.stdout.write('  - staff_demo / (password you passed via --password)')

    def _ensure_demo_users(self, password, main_location):
        User = get_user_model()

        admin_user, created_admin = User.objects.get_or_create(
            username='admin_demo',
            defaults={
                'role': 'ADMIN',
                'email': 'admin_demo@example.com',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created_admin:
            admin_user.set_password(password)
            admin_user.save(update_fields=['password'])

        manager_user, created_manager = User.objects.get_or_create(
            username='manager_demo',
            defaults={
                'role': 'MANAGER',
                'email': 'manager_demo@example.com',
                'is_staff': True,
            },
        )
        if created_manager:
            manager_user.set_password(password)
            manager_user.save(update_fields=['password'])

        staff_user, created_staff = User.objects.get_or_create(
            username='staff_demo',
            defaults={
                'role': 'STAFF',
                'email': 'staff_demo@example.com',
                'location': main_location,
                'is_staff': False,
            },
        )
        if created_staff:
            staff_user.set_password(password)
            staff_user.save(update_fields=['password'])

        return admin_user

    def _ensure_ingredients(self):
        # name, unit, reorder_level, cost_per_unit
        ingredient_rows = [
            ('Flour', 'kg', Decimal('10.00'), Decimal('2.00')),
            ('Sugar', 'kg', Decimal('5.00'), Decimal('1.50')),
            ('Butter', 'kg', Decimal('3.00'), Decimal('8.00')),
            ('Eggs', 'pcs', Decimal('48.00'), Decimal('0.30')),
            ('Milk', 'L', Decimal('5.00'), Decimal('1.20')),
            ('Yeast', 'kg', Decimal('1.00'), Decimal('12.00')),
            ('Chocolate', 'kg', Decimal('4.00'), Decimal('9.50')),
            ('Vanilla Extract', 'mL', Decimal('500.00'), Decimal('0.02')),
        ]

        ingredients = {}
        for name, unit, reorder_level, cost_per_unit in ingredient_rows:
            ing, _ = Ingredient.objects.get_or_create(
                name=name,
                defaults={
                    'unit': unit,
                    'reorder_level': reorder_level,
                    'cost_per_unit': cost_per_unit,
                    'is_active': True,
                },
            )

            # Keep seed fields synced.
            updates = {}
            if ing.unit != unit:
                updates['unit'] = unit
            if ing.reorder_level != reorder_level:
                updates['reorder_level'] = reorder_level
            if ing.cost_per_unit != cost_per_unit:
                updates['cost_per_unit'] = cost_per_unit
            if not ing.is_active:
                updates['is_active'] = True

            if updates:
                for k, v in updates.items():
                    setattr(ing, k, v)
                ing.save(update_fields=list(updates.keys()))

            ingredients[name] = ing

        return ingredients
