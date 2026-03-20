from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from inventory.models import StockMovement, Ingredient, Stock
from recipes.models import ProductionBatch
from orders.models import CustomerOrder
import logging

logger = logging.getLogger('inventory')


class Command(BaseCommand):
    help = 'Generate and send weekly inventory summary report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send email with weekly summary',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to include in summary (default: 7)',
        )

    def handle(self, *args, **options):
        days = options['days']
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Generating {days}-day inventory summary...')
        )
        
        # Stock movements summary
        movements = StockMovement.objects.filter(
            created_at__date__gte=start_date
        )
        
        stock_in = movements.filter(movement_type='IN').aggregate(
            count=Count('id'),
            total=Sum('quantity')
        )
        
        stock_out = movements.filter(movement_type='OUT').aggregate(
            count=Count('id'),
            total=Sum('quantity')
        )
        
        waste = movements.filter(movement_type='WASTE').aggregate(
            count=Count('id'),
            total=Sum('quantity')
        )
        
        # Production summary
        production_batches = ProductionBatch.objects.filter(
            production_date__gte=start_date,
            status='COMPLETED'
        )
        
        production_count = production_batches.count()
        
        # Orders summary
        orders = CustomerOrder.objects.filter(
            created_at__date__gte=start_date
        )
        
        orders_summary = {
            'total': orders.count(),
            'completed': orders.filter(status='COMPLETED').count(),
            'in_progress': orders.filter(status='IN_PROGRESS').count(),
            'cancelled': orders.filter(status='CANCELLED').count(),
        }
        
        # Low stock items
        low_stock_count = 0
        for ingredient in Ingredient.objects.filter(is_active=True):
            if ingredient.get_total_stock() < ingredient.reorder_level:
                low_stock_count += 1
        
        # Expiring stock
        expiring_soon = Stock.objects.filter(
            expiration_date__lte=today + timedelta(days=7),
            expiration_date__gte=today,
            quantity__gt=0
        ).count()
        
        # Display summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'INVENTORY SUMMARY ({start_date} to {today})'))
        self.stdout.write('='*60 + '\n')
        
        self.stdout.write(self.style.WARNING('Stock Movements:'))
        self.stdout.write(f"  Stock In: {stock_in['count'] or 0} transactions")
        self.stdout.write(f"  Stock Out: {stock_out['count'] or 0} transactions")
        self.stdout.write(f"  Waste: {waste['count'] or 0} transactions\n")
        
        self.stdout.write(self.style.WARNING('Production:'))
        self.stdout.write(f"  Completed Batches: {production_count}\n")
        
        self.stdout.write(self.style.WARNING('Customer Orders:'))
        self.stdout.write(f"  Total Orders: {orders_summary['total']}")
        self.stdout.write(f"  Completed: {orders_summary['completed']}")
        self.stdout.write(f"  In Progress: {orders_summary['in_progress']}")
        self.stdout.write(f"  Cancelled: {orders_summary['cancelled']}\n")
        
        self.stdout.write(self.style.WARNING('Alerts:'))
        if low_stock_count > 0:
            self.stdout.write(
                self.style.ERROR(f"  Low Stock Items: {low_stock_count}")
            )
        else:
            self.stdout.write(f"  Low Stock Items: {low_stock_count}")
        
        if expiring_soon > 0:
            self.stdout.write(
                self.style.ERROR(f"  Items Expiring Soon (7 days): {expiring_soon}")
            )
        else:
            self.stdout.write(f"  Items Expiring Soon (7 days): {expiring_soon}")
        
        self.stdout.write('\n' + '='*60 + '\n')
        
        # Send email if requested
        if options['send_email']:
            self._send_email_summary(
                start_date, today, stock_in, stock_out, waste,
                production_count, orders_summary, low_stock_count, expiring_soon
            )
        
        logger.info(f'Weekly summary generated for {start_date} to {today}')
        return f"Summary generated for {days} days"
    
    def _send_email_summary(self, start_date, end_date, stock_in, stock_out, 
                           waste, production_count, orders_summary, 
                           low_stock_count, expiring_soon):
        """Send email with weekly summary"""
        try:
            subject = f'Weekly Inventory Summary - {start_date} to {end_date}'
            
            message_lines = [
                f'INVENTORY SUMMARY REPORT',
                f'Period: {start_date} to {end_date}',
                '',
                'STOCK MOVEMENTS:',
                f'  Stock In: {stock_in["count"] or 0} transactions',
                f'  Stock Out: {stock_out["count"] or 0} transactions',
                f'  Waste: {waste["count"] or 0} transactions',
                '',
                'PRODUCTION:',
                f'  Completed Batches: {production_count}',
                '',
                'CUSTOMER ORDERS:',
                f'  Total Orders: {orders_summary["total"]}',
                f'  Completed: {orders_summary["completed"]}',
                f'  In Progress: {orders_summary["in_progress"]}',
                f'  Cancelled: {orders_summary["cancelled"]}',
                '',
                'ALERTS:',
                f'  Low Stock Items: {low_stock_count}',
                f'  Items Expiring Soon (7 days): {expiring_soon}',
            ]
            
            if low_stock_count > 0 or expiring_soon > 0:
                message_lines.append('')
                message_lines.append('ACTION REQUIRED:')
                if low_stock_count > 0:
                    message_lines.append(
                        f'  - Review and reorder {low_stock_count} low stock items'
                    )
                if expiring_soon > 0:
                    message_lines.append(
                        f'  - Check {expiring_soon} items expiring within 7 days'
                    )
            
            message = '\n'.join(message_lines)
            
            # Get recipient email from settings or use default
            recipient_email = getattr(settings, 'INVENTORY_ALERT_EMAIL', settings.DEFAULT_FROM_EMAIL)
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient_email],
                fail_silently=False,
            )
            
            self.stdout.write(self.style.SUCCESS(f'Email summary sent to {recipient_email}'))
            logger.info(f'Weekly summary email sent to {recipient_email}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {str(e)}'))
            logger.error(f'Failed to send weekly summary email: {str(e)}')
