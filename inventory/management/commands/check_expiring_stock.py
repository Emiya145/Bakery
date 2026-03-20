from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from inventory.models import Stock
import logging

logger = logging.getLogger('inventory')


class Command(BaseCommand):
    help = 'Check for expiring stock and send alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look ahead for expiring stock (default: 7)',
        )
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send email alerts for expiring stock',
        )

    def handle(self, *args, **options):
        days_ahead = options['days']
        today = timezone.now().date()
        expiry_threshold = today + timedelta(days=days_ahead)
        
        self.stdout.write(
            self.style.SUCCESS(f'Checking for stock expiring within {days_ahead} days...')
        )
        
        # Find expiring stock
        expiring_stock = Stock.objects.filter(
            expiration_date__lte=expiry_threshold,
            expiration_date__gte=today,
            quantity__gt=0
        ).select_related('ingredient', 'location').order_by('expiration_date')
        
        # Find already expired stock
        expired_stock = Stock.objects.filter(
            expiration_date__lt=today,
            quantity__gt=0
        ).select_related('ingredient', 'location').order_by('expiration_date')
        
        if expired_stock.exists():
            self.stdout.write(
                self.style.ERROR(f'Found {expired_stock.count()} EXPIRED stock items:')
            )
            for stock in expired_stock:
                days_expired = (today - stock.expiration_date).days
                self.stdout.write(
                    self.style.ERROR(
                        f"  - {stock.ingredient.name} at {stock.location.name}: "
                        f"{stock.quantity} {stock.ingredient.unit} "
                        f"(expired {days_expired} days ago on {stock.expiration_date})"
                    )
                )
                logger.error(
                    f"Expired stock: {stock.ingredient.name} at {stock.location.name}, "
                    f"expired {days_expired} days ago"
                )
        
        if expiring_stock.exists():
            self.stdout.write(
                self.style.WARNING(f'Found {expiring_stock.count()} expiring stock items:')
            )
            for stock in expiring_stock:
                days_until_expiry = (stock.expiration_date - today).days
                self.stdout.write(
                    f"  - {stock.ingredient.name} at {stock.location.name}: "
                    f"{stock.quantity} {stock.ingredient.unit} "
                    f"(expires in {days_until_expiry} days on {stock.expiration_date})"
                )
                logger.warning(
                    f"Expiring stock: {stock.ingredient.name} at {stock.location.name}, "
                    f"expires in {days_until_expiry} days"
                )
            
            # Send email if requested
            if options['send_email']:
                self._send_email_alert(expiring_stock, expired_stock, days_ahead)
        else:
            if not expired_stock.exists():
                self.stdout.write(
                    self.style.SUCCESS('No expiring or expired stock found')
                )
        
        return f"Found {expired_stock.count()} expired and {expiring_stock.count()} expiring items"
    
    def _send_email_alert(self, expiring_stock, expired_stock, days_ahead):
        """Send email alert for expiring stock"""
        try:
            subject = f'Stock Expiration Alert - {expiring_stock.count()} Items Expiring Soon'
            
            message_lines = []
            
            if expired_stock.exists():
                message_lines.append(f'URGENT - {expired_stock.count()} items are ALREADY EXPIRED:\n')
                for stock in expired_stock:
                    today = timezone.now().date()
                    days_expired = (today - stock.expiration_date).days
                    message_lines.append(
                        f"- {stock.ingredient.name} at {stock.location.name}: "
                        f"{stock.quantity} {stock.ingredient.unit} "
                        f"(expired {days_expired} days ago on {stock.expiration_date})"
                    )
                message_lines.append('\n')
            
            if expiring_stock.exists():
                message_lines.append(
                    f'The following items will expire within {days_ahead} days:\n'
                )
                for stock in expiring_stock:
                    today = timezone.now().date()
                    days_until_expiry = (stock.expiration_date - today).days
                    message_lines.append(
                        f"- {stock.ingredient.name} at {stock.location.name}: "
                        f"{stock.quantity} {stock.ingredient.unit} "
                        f"(expires in {days_until_expiry} days on {stock.expiration_date})"
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
            logger.info(f'Expiring stock email alert sent to {recipient_email}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {str(e)}'))
            logger.error(f'Failed to send expiring stock email: {str(e)}')
