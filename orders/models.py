from django.db import models
from django.core.validators import MinValueValidator, EmailValidator
from django.db.models import Sum
from django.utils import timezone


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, validators=[EmailValidator()])
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    company = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders_customer'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_total_orders_value(self):
        """Calculate total value of all orders"""
        total = self.orders.filter(
            status__in=['CONFIRMED', 'COMPLETED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        return total
    
    def get_order_count(self):
        """Get total number of orders"""
        return self.orders.count()


class CustomerOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('READY', 'Ready for Pickup'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='NORMAL')
    order_date = models.DateTimeField(auto_now_add=True)
    requested_delivery_date = models.DateTimeField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT,
        related_name='customer_orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'orders_customer_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'order_date']),
            models.Index(fields=['order_number']),
            models.Index(fields=['requested_delivery_date']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer.name}"
    
    def calculate_subtotal(self):
        """Calculate subtotal from order items"""
        subtotal = self.items.aggregate(
            total=Sum(models.F('quantity') * models.F('unit_price'))
        )['total'] or 0
        return subtotal
    
    def calculate_total(self):
        """Calculate total amount with discounts"""
        subtotal = self.calculate_subtotal()
        
        # Apply percentage discount first
        if self.discount_percentage > 0:
            subtotal = subtotal * (1 - self.discount_percentage / 100)
        
        # Then apply fixed amount discount
        total = subtotal - self.discount_amount
        self.total_amount = max(0, total)  # Ensure total is not negative
        self.save(update_fields=['total_amount'])
        return self.total_amount
    
    def can_be_produced(self):
        """Check if all products in order are available for production"""
        for item in self.items.all():
            # Check if product has active recipe
            if not item.product.active_recipe:
                return False, f"{item.product.name} has no active recipe"
            
            # Check if ingredients are available
            recipe = item.product.active_recipe
            from inventory.models import Stock
            
            for recipe_ingredient in recipe.ingredients.all():
                if recipe_ingredient.optional:
                    continue
                    
                required_qty = recipe_ingredient.quantity * item.quantity
                
                # Check stock availability (simplified - would need location)
                available_stock = Stock.objects.filter(
                    ingredient=recipe_ingredient.ingredient,
                    quantity__gt=0
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                if available_stock < required_qty:
                    return False, f"Insufficient {recipe_ingredient.ingredient.name}"
        
        return True, "All ingredients available"
    
    def start_production(self, user, location=None):
        """Start production for this order"""
        can_produce, message = self.can_be_produced()
        if not can_produce:
            return False, message
        
        from inventory.services import InventoryService
        from recipes.models import ProductionBatch
        
        if location is None:
            location = user.location or user.location_set.first()
        
        if not location:
            return False, "No production location specified"
        
        # Create production batches and deduct ingredients
        service = InventoryService()
        batches_created = []
        
        for item in self.items.all():
            recipe = item.product.active_recipe
            
            # Create production batch
            batch = ProductionBatch.objects.create(
                recipe=recipe,
                quantity_produced=item.quantity,
                location=location,
                status='IN_PROGRESS',
                batch_number=f"ORD-{self.order_number}-{item.product.id}",
                production_date=timezone.now().date(),
                created_by=user
            )
            batches_created.append(batch)
            
            # Deduct ingredients
            try:
                service.deduct_for_production(
                    recipe=recipe,
                    quantity_produced=item.quantity,
                    location=location,
                    user=user,
                    reference=self.order_number
                )
            except Exception as e:
                return False, f"Error deducting ingredients for {item.product.name}: {str(e)}"
        
        # Update order status
        self.status = 'IN_PROGRESS'
        self.save(update_fields=['status'])
        
        return True, f"Production started for {len(batches_created)} items"
    
    def mark_as_completed(self, user):
        """Mark order as completed"""
        self.status = 'COMPLETED'
        self.actual_delivery_date = timezone.now()
        self.save(update_fields=['status', 'actual_delivery_date'])


class CustomerOrderItem(models.Model):
    order = models.ForeignKey(
        CustomerOrder, 
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product', 
        on_delete=models.PROTECT,
        related_name='order_items'
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
    notes = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'orders_customer_order_item'
        unique_together = [['order', 'product']]
        ordering = ['product__name']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.product.name}"
    
    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.unit_price
    
    @property
    def cost_price(self):
        """Get cost price for this item"""
        if self.product.cost_price:
            return self.quantity * self.product.cost_price
        return 0
    
    @property
    def profit(self):
        """Calculate profit for this item"""
        return self.total_price - self.cost_price
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return (self.profit / self.cost_price) * 100
        return 0
