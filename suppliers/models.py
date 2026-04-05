from django.db import models
from django.core.validators import MinValueValidator, EmailValidator
from django.db.models import Avg, F, Sum


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True, validators=[EmailValidator()])
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    lead_time_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(0)],
        help_text="Standard lead time in days for orders"
    )
    minimum_order_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum order value in currency"
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        help_text="Payment terms (e.g., 'Net 30', 'COD')"
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'suppliers_supplier'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_active_price_list(self):
        """Get currently active prices for this supplier"""
        return self.prices.filter(
            valid_until__isnull=True
        ).select_related('ingredient')
    
    def get_price_for_ingredient(self, ingredient):
        """Get current price for a specific ingredient"""
        try:
            return self.prices.get(
                ingredient=ingredient,
                valid_until__isnull=True
            ).price_per_unit
        except SupplierPrice.DoesNotExist:
            return None
    
    def get_average_lead_time(self):
        """Calculate average lead time from recent orders"""
        recent_orders = self.orders.filter(
            status='COMPLETED'
        ).order_by('-created_at')[:10]
        
        if recent_orders:
            lead_times = []
            for order in recent_orders:
                if order.actual_delivery_date:
                    lead_time = (order.actual_delivery_date - order.order_date).days
                    lead_times.append(lead_time)
            
            if lead_times:
                return sum(lead_times) / len(lead_times)
        
        return self.lead_time_days


class SupplierPrice(models.Model):
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.CASCADE,
        related_name='prices'
    )
    ingredient = models.ForeignKey(
        'inventory.Ingredient', 
        on_delete=models.CASCADE,
        related_name='supplier_prices'
    )
    price_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    unit = models.CharField(
        max_length=20,
        help_text="Unit for this price (should match ingredient unit)"
    )
    valid_from = models.DateField()
    valid_until = models.DateField(
        null=True, 
        blank=True,
        help_text="Leave blank for current price"
    )
    minimum_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum quantity for this price (tier pricing)"
    )
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'suppliers_price'
        indexes = [
            models.Index(fields=['supplier', 'ingredient']),
            models.Index(fields=['ingredient', 'valid_from']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
        unique_together = [['supplier', 'ingredient', 'valid_from']]
        ordering = ['-valid_from']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.ingredient.name}: ${self.price_per_unit}/{self.unit}"
    
    @property
    def is_current(self):
        """Check if this price is currently valid"""
        from django.utils import timezone
        today = timezone.now().date()
        return (self.valid_from <= today and 
                (self.valid_until is None or self.valid_until >= today))


class SupplierOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent to Supplier'),
        ('CONFIRMED', 'Confirmed by Supplier'),
        ('SHIPPED', 'Shipped'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    order_date = models.DateField()
    expected_delivery_date = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT,
        related_name='supplier_orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'suppliers_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['status', 'order_date']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.supplier.name}"
    
    def calculate_total(self):
        """Calculate total amount from order items"""
        total = self.items.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total
    
    def mark_as_received(self, user, actual_date=None):
        """Mark order as received and update stock"""
        from inventory.services import InventoryService
        
        if actual_date is None:
            from django.utils import timezone
            actual_date = timezone.now().date()
        
        self.status = 'RECEIVED'
        self.actual_delivery_date = actual_date
        self.save(update_fields=['status', 'actual_delivery_date'])
        
        # Process order items and update stock
        service = InventoryService()
        order_items = []
        
        for item in self.items.all():
            order_items.append({
                'ingredient': item.ingredient,
                'quantity': item.quantity_received or item.quantity,
                'batch_number': item.batch_number,
                'expiration_date': item.expiration_date
            })
        
        if order_items:
            # Need a location - use first user's location or default
            location = user.location or user.location_set.first()
            if location:
                service.receive_supplier_order(
                    order_items=order_items,
                    location=location,
                    user=user,
                    reference=self.order_number
                )
        
        return True


class SupplierOrderItem(models.Model):
    order = models.ForeignKey(
        SupplierOrder, 
        on_delete=models.CASCADE,
        related_name='items'
    )
    ingredient = models.ForeignKey(
        'inventory.Ingredient', 
        on_delete=models.PROTECT,
        related_name='supplier_order_items'
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    quantity_received = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Actual quantity received (may differ from ordered)"
    )
    batch_number = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Batch number from supplier"
    )
    expiration_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Expiration date for this batch"
    )
    notes = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'suppliers_order_item'
        unique_together = [['order', 'ingredient']]
        ordering = ['ingredient__name']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.ingredient.name}"
    
    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.unit_price
    
    @property
    def is_fully_received(self):
        """Check if this item was fully received"""
        if self.quantity_received is None:
            return False
        return self.quantity_received >= self.quantity
    
    @property
    def reception_variance(self):
        """Calculate variance between ordered and received quantities"""
        if self.quantity_received is None:
            return None
        return self.quantity_received - self.quantity
