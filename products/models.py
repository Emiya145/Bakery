from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'products_category'
        ordering = ['name']
        verbose_name_plural = 'Product Categories'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    UNITS = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('L', 'Liters'),
        ('mL', 'Milliliters'),
        ('units', 'Units'),
        ('pcs', 'Pieces'),
        ('boxes', 'Boxes'),
        ('loaves', 'Loaves'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.PROTECT,
        related_name='products'
    )
    unit = models.CharField(max_length=20, choices=UNITS)
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Selling price per unit"
    )
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Cost price per unit (calculated from recipe)"
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='products/',
        null=True, 
        blank=True,
        help_text="Product image"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products_product'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.unit})"
    
    def calculate_cost_price(self):
        """Calculate cost price based on active recipe"""
        active_recipe = self.recipes.filter(is_active=True).first()
        if active_recipe:
            return active_recipe.calculate_cost_per_unit()
        return None
    
    def update_cost_price(self):
        """Update the cost_price field based on current recipe"""
        cost = self.calculate_cost_price()
        if cost is not None:
            self.cost_price = cost
            self.save(update_fields=['cost_price'])
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price and self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return None
    
    @property
    def active_recipe(self):
        """Get the currently active recipe"""
        return self.recipes.filter(is_active=True).first()


class ProductStock(models.Model):
    """
    Tracks finished goods inventory (produced products)
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='stock'
    )
    location = models.ForeignKey(
        'inventory.Location', 
        on_delete=models.PROTECT,
        related_name='product_stock'
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    batch_number = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Production batch number"
    )
    production_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date this batch was produced"
    )
    expiration_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Expiration date for this batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products_stock'
        unique_together = [['product', 'location', 'batch_number']]
        ordering = ['expiration_date', 'created_at']
        indexes = [
            models.Index(fields=['product', 'location']),
            models.Index(fields=['expiration_date']),
        ]
    
    def __str__(self):
        batch_info = f" (Batch: {self.batch_number})" if self.batch_number else ""
        return f"{self.product.name} at {self.location.name}: {self.quantity} {self.product.unit}{batch_info}"
    
    @property
    def is_expiring_soon(self):
        """Check if product expires within 3 days"""
        if not self.expiration_date:
            return False
        from django.utils import timezone
        return (self.expiration_date - timezone.now().date()).days <= 3
    
    @property
    def is_expired(self):
        """Check if product is already expired"""
        if not self.expiration_date:
            return False
        from django.utils import timezone
        return self.expiration_date < timezone.now().date()
    
    def get_total_stock(self):
        """Get total stock across all locations"""
        result = ProductStock.objects.filter(product=self.product).aggregate(
            total=Sum('quantity')
        )
        return result['total'] or 0
