from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db.models import Sum
from django.conf import settings
from inventory.models import Ingredient, Stock
import logging

logger = logging.getLogger('inventory')


class Command(BaseCommand):
    help = 'Check for low stock ingredients and send alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send email alerts for low stock items',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking for low stock ingredients...'))
        
        low_stock_items = []
        
        for ingredient in Ingredient.objects.filter(is_active=True):
            total_stock = ingredient.get_total_stock()
            
            if total_stock < ingredient.reorder_level:
                shortage = ingredient.reorder_level - total_stock
                low_stock_items.append({
                    'name': ingredient.name,
                    'current': total_stock,
                    'reorder_level': ingredient.reorder_level,
                    'shortage': shortage,
                    'unit': ingredient.unit
                })
                
                logger.warning(
                    f"Low stock alert: {ingredient.name} - "
                    f"Current: {total_stock} {ingredient.unit}, "
                    f"Reorder level: {ingredient.reorder_level} {ingredient.unit}"
                )
        
        if low_stock_items:
            self.stdout.write(
                self.style.WARNING(f'Found {len(low_stock_items)} low stock items')
            )
            
            # Display low stock items
            for item in low_stock_items:
                self.stdout.write(
                    f"  - {item['name']}: {item['current']} {item['unit']} "
                    f"(need {item['shortage']} more to reach {item['reorder_level']} {item['unit']})"
                )
            
            # Send email if requested
            if options['send_email']:
                self._send_email_alert(low_stock_items)
        else:
            self.stdout.write(self.style.SUCCESS('All ingredients are adequately stocked'))
        
        return f"Checked {Ingredient.objects.filter(is_active=True).count()} ingredients, found {len(low_stock_items)} low stock items"
    
    def _send_email_alert(self, low_stock_items):
        """Send email alert for low stock items"""
        try:
            subject = f'Low Stock Alert - {len(low_stock_items)} Items Need Reordering'
            
            message_lines = ['The following ingredients are below reorder level:\n']
            for item in low_stock_items:
                message_lines.append(
                    f"- {item['name']}: {item['current']} {item['unit']} "
                    f"(Reorder level: {item['reorder_level']} {item['unit']}, "
                    f"Shortage: {item['shortage']} {item['unit']})"
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
            
            self.stdout.write(self.style.SUCCESS(f'Email alert sent to {recipient_email}'))
            logger.info(f'Low stock email alert sent to {recipient_email}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {str(e)}'))
            logger.error(f'Failed to send low stock email: {str(e)}')
