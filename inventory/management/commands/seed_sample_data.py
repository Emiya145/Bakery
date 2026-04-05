from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import Ingredient, Location, Stock, StockMovement
from orders.models import Customer, CustomerOrder, CustomerOrderItem
from products.models import Product, ProductCategory, ProductStock
from recipes.models import ProductionBatch, Recipe, RecipeIngredient
from suppliers.models import Supplier, SupplierOrder, SupplierOrderItem, SupplierPrice


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
            User = get_user_model()
            seed_user = (
                User.objects.filter(is_superuser=True).first()
                or User.objects.filter(is_staff=True).first()
                or User.objects.first()
            )

        if seed_user is None:
            self.stdout.write(
                self.style.ERROR(
                    'No user exists to attribute records to. Create a user first or run without --skip-users.'
                )
            )
            return

        ingredients = self._ensure_ingredients()

        stock_plan = [
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

        products = self._ensure_products_and_recipes(ingredients, seed_user)
        self._ensure_product_stock(products, main_location, today)
        self._ensure_suppliers(ingredients, seed_user, today)
        self._ensure_customers_and_orders(products, seed_user)
        self._ensure_production_sample(products, main_location, seed_user, today)

        self.stdout.write(self.style.SUCCESS('Sample data seeded.'))
        self.stdout.write(f'Locations: {Location.objects.count()}')
        self.stdout.write(f'Ingredients: {Ingredient.objects.count()}')
        self.stdout.write(f'Stock batches created: {created_stocks}, updated: {updated_stocks}')
        self.stdout.write(f'Stock movements (SEED*): {StockMovement.objects.filter(reference__startswith="SEED").count()}')
        self.stdout.write(f'Products: {Product.objects.count()} | Recipes: {Recipe.objects.count()}')
        self.stdout.write(f'Suppliers: {Supplier.objects.count()} | Customer orders: {CustomerOrder.objects.count()}')

        if not options['skip_users']:
            self.stdout.write('Demo users (created if missing):')
            self.stdout.write('  - admin_demo / (password from --password)')
            self.stdout.write('  - manager_demo / (password from --password)')
            self.stdout.write('  - staff_demo / (password from --password)')

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

    def _ensure_products_and_recipes(self, ingredients, seed_user):
        """Categories, products, active recipes with ingredients."""
        cat_bread, _ = ProductCategory.objects.get_or_create(
            name='Breads',
            defaults={'description': 'Artisan and daily breads', 'is_active': True},
        )
        cat_pastry, _ = ProductCategory.objects.get_or_create(
            name='Pastries',
            defaults={'description': 'Viennoiserie and desserts', 'is_active': True},
        )

        product_specs = [
            {
                'name': 'Sourdough Loaf',
                'category': cat_bread,
                'unit': 'loaves',
                'selling_price': Decimal('6.50'),
                'description': 'Slow-fermented sourdough',
                'yield_qty': Decimal('1'),
                'yield_unit': 'loaves',
                'lines': [
                    ('Flour', Decimal('0.48')),
                    ('Yeast', Decimal('0.015')),
                    ('Sugar', Decimal('0.02')),
                    ('Butter', Decimal('0.03')),
                    ('Milk', Decimal('0.10')),
                ],
            },
            {
                'name': 'Butter Croissant',
                'category': cat_pastry,
                'unit': 'pcs',
                'selling_price': Decimal('3.25'),
                'description': 'Layered butter croissant (per piece)',
                'yield_qty': Decimal('12'),
                'yield_unit': 'pcs',
                'lines': [
                    ('Flour', Decimal('0.40')),
                    ('Butter', Decimal('0.25')),
                    ('Eggs', Decimal('1')),
                    ('Milk', Decimal('0.15')),
                    ('Sugar', Decimal('0.05')),
                    ('Yeast', Decimal('0.01')),
                ],
            },
            {
                'name': 'Chocolate Brownie Tray',
                'category': cat_pastry,
                'unit': 'pcs',
                'selling_price': Decimal('2.75'),
                'description': 'Tray cut into 24 pieces',
                'yield_qty': Decimal('24'),
                'yield_unit': 'pcs',
                'lines': [
                    ('Flour', Decimal('0.30')),
                    ('Sugar', Decimal('0.40')),
                    ('Butter', Decimal('0.30')),
                    ('Eggs', Decimal('4')),
                    ('Chocolate', Decimal('0.20')),
                    ('Vanilla Extract', Decimal('10')),
                ],
            },
        ]

        products = {}
        for spec in product_specs:
            product, _ = Product.objects.get_or_create(
                name=spec['name'],
                defaults={
                    'category': spec['category'],
                    'unit': spec['unit'],
                    'selling_price': spec['selling_price'],
                    'description': spec['description'],
                    'is_active': True,
                },
            )
            changed = False
            for field in ('category', 'unit', 'selling_price', 'description'):
                val = spec[field] if field != 'category' else spec['category']
                if getattr(product, field) != val:
                    setattr(product, field, val)
                    changed = True
            if changed:
                product.save()

            recipe, created = Recipe.objects.get_or_create(
                product=product,
                version=1,
                defaults={
                    'yield_quantity': spec['yield_qty'],
                    'yield_unit': spec['yield_unit'],
                    'is_active': True,
                    'instructions': f"Standard production for {product.name}.",
                    'prep_time_minutes': 30,
                    'cook_time_minutes': 25,
                    'created_by': seed_user,
                },
            )
            if created:
                Recipe.objects.filter(product=product).exclude(pk=recipe.pk).update(is_active=False)
            else:
                recipe.yield_quantity = spec['yield_qty']
                recipe.yield_unit = spec['yield_unit']
                recipe.is_active = True
                recipe.save(update_fields=['yield_quantity', 'yield_unit', 'is_active'])
                Recipe.objects.filter(product=product).exclude(pk=recipe.pk).update(is_active=False)

            for ing_name, qty in spec['lines']:
                RecipeIngredient.objects.update_or_create(
                    recipe=recipe,
                    ingredient=ingredients[ing_name],
                    defaults={'quantity': qty, 'optional': False},
                )

            product.update_cost_price()
            products[spec['name']] = product

        return products

    def _ensure_product_stock(self, products, main_location, today):
        plan = [
            ('Sourdough Loaf', 'FG-LOAF-001', Decimal('18'), today + timedelta(days=2)),
            ('Butter Croissant', 'FG-CRO-001', Decimal('36'), today + timedelta(days=1)),
            ('Chocolate Brownie Tray', 'FG-BRW-001', Decimal('48'), today + timedelta(days=5)),
        ]
        for name, batch, qty, exp in plan:
            product = products[name]
            ps, created = ProductStock.objects.get_or_create(
                product=product,
                location=main_location,
                batch_number=batch,
                defaults={
                    'quantity': qty,
                    'production_date': today - timedelta(days=1),
                    'expiration_date': exp,
                },
            )
            if not created:
                if ps.quantity != qty or ps.expiration_date != exp:
                    ps.quantity = qty
                    ps.expiration_date = exp
                    ps.production_date = today - timedelta(days=1)
                    ps.save(update_fields=['quantity', 'expiration_date', 'production_date'])

    def _ensure_suppliers(self, ingredients, seed_user, today):
        grain, _ = Supplier.objects.get_or_create(
            name='Grain & Co Wholesale',
            defaults={
                'contact_person': 'Alex Miller',
                'email': 'orders@grainco.example.com',
                'phone': '555-2001',
                'address': '900 Mill Rd',
                'lead_time_days': 5,
                'minimum_order_value': Decimal('150.00'),
                'payment_terms': 'Net 30',
                'is_active': True,
            },
        )
        dairy, _ = Supplier.objects.get_or_create(
            name='Dairy Fresh Suppliers',
            defaults={
                'contact_person': 'Sam Patel',
                'email': 'sales@dairyfresh.example.com',
                'phone': '555-2002',
                'lead_time_days': 3,
                'payment_terms': 'COD',
                'is_active': True,
            },
        )

        price_start = date(2024, 1, 1)
        for sup, ing_name, price in [
            (grain, 'Flour', Decimal('1.95')),
            (grain, 'Sugar', Decimal('1.45')),
            (grain, 'Yeast', Decimal('11.50')),
            (dairy, 'Milk', Decimal('1.10')),
            (dairy, 'Butter', Decimal('7.80')),
            (dairy, 'Eggs', Decimal('0.28')),
        ]:
            ing = ingredients[ing_name]
            SupplierPrice.objects.update_or_create(
                supplier=sup,
                ingredient=ing,
                valid_from=price_start,
                defaults={
                    'price_per_unit': price,
                    'unit': ing.unit,
                    'valid_until': None,
                },
            )

        po, po_created = SupplierOrder.objects.get_or_create(
            order_number='PO-SEED-001',
            defaults={
                'supplier': grain,
                'status': 'SENT',
                'order_date': today - timedelta(days=2),
                'expected_delivery_date': today + timedelta(days=3),
                'notes': 'Seed supplier order',
                'created_by': seed_user,
            },
        )
        if po_created:
            SupplierOrderItem.objects.get_or_create(
                order=po,
                ingredient=ingredients['Flour'],
                defaults={'quantity': Decimal('50'), 'unit_price': Decimal('1.95')},
            )
            SupplierOrderItem.objects.get_or_create(
                order=po,
                ingredient=ingredients['Sugar'],
                defaults={'quantity': Decimal('20'), 'unit_price': Decimal('1.45')},
            )
            po.calculate_total()

    def _ensure_customers_and_orders(self, products, seed_user):
        cust1, _ = Customer.objects.get_or_create(
            name="Riverside Cafe",
            defaults={
                'email': 'orders@riversidecafe.example.com',
                'phone': '555-3001',
                'address': '10 River Rd',
                'company': 'Riverside Cafe LLC',
                'is_active': True,
            },
        )
        cust2, _ = Customer.objects.get_or_create(
            name='Bob Smith',
            defaults={
                'email': 'bob.smith@example.com',
                'phone': '555-3002',
                'is_active': True,
            },
        )

        order1, o1_created = CustomerOrder.objects.get_or_create(
            order_number='CO-SEED-001',
            defaults={
                'customer': cust1,
                'status': 'CONFIRMED',
                'priority': 'NORMAL',
                'notes': 'Morning delivery slot',
                'created_by': seed_user,
            },
        )
        if o1_created:
            CustomerOrderItem.objects.get_or_create(
                order=order1,
                product=products['Sourdough Loaf'],
                defaults={'quantity': Decimal('10'), 'unit_price': Decimal('6.50')},
            )
            CustomerOrderItem.objects.get_or_create(
                order=order1,
                product=products['Butter Croissant'],
                defaults={'quantity': Decimal('24'), 'unit_price': Decimal('3.25')},
            )
            order1.calculate_total()

        order2, o2_created = CustomerOrder.objects.get_or_create(
            order_number='CO-SEED-002',
            defaults={
                'customer': cust2,
                'status': 'READY',
                'priority': 'HIGH',
                'created_by': seed_user,
            },
        )
        if o2_created:
            CustomerOrderItem.objects.get_or_create(
                order=order2,
                product=products['Chocolate Brownie Tray'],
                defaults={'quantity': Decimal('6'), 'unit_price': Decimal('2.75')},
            )
            order2.calculate_total()

    def _ensure_production_sample(self, products, main_location, seed_user, today):
        product = products['Sourdough Loaf']
        recipe = product.recipes.filter(is_active=True).first()
        if not recipe:
            return
        ProductionBatch.objects.get_or_create(
            batch_number='PROD-SEED-001',
            defaults={
                'recipe': recipe,
                'quantity_produced': Decimal('5'),
                'location': main_location,
                'status': 'COMPLETED',
                'production_date': today - timedelta(days=1),
                'notes': 'Seed production batch',
                'created_by': seed_user,
            },
        )
