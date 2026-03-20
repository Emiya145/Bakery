from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum
from django.utils import timezone


class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_location'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def total_ingredients(self):
        return self.stock_set.values('ingredient').distinct().count()


class Ingredient(models.Model):
    UNITS = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('L', 'Liters'),
        ('mL', 'Milliliters'),
        ('units', 'Units'),
        ('pcs', 'Pieces'),
        ('boxes', 'Boxes'),
    ]
    
    name = models.CharField(max_length=200, db_index=True, unique=True)
    unit = models.CharField(max_length=20, choices=UNITS)
    reorder_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Minimum quantity before reordering is needed"
    )
    cost_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Standard cost per unit for calculations"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_ingredient'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.unit})"
    
    def get_total_stock(self):
        """Get total stock across all locations"""
        result = self.stock_set.aggregate(
            total=Sum('quantity')
        )
        return result['total'] or 0
    
    def get_stock_by_location(self):
        """Get stock levels by location"""
        return self.stock_set.select_related('location').all()
    
    def is_low_stock(self):
        """Check if ingredient is below reorder level"""
        return self.get_total_stock() < self.reorder_level


class Stock(models.Model):
    ingredient = models.ForeignKey(
        Ingredient, 
        on_delete=models.PROTECT,
        related_name='stock_set'
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.PROTECT,
        related_name='stock_set'
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Current quantity in stock"
    )
    expiration_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Expiration date for this batch"
    )
    batch_number = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Batch or lot number for traceability"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_stock'
        indexes = [
            models.Index(fields=['ingredient', 'location']),
            models.Index(fields=['expiration_date']),
            models.Index(fields=['batch_number']),
        ]
        unique_together = [['ingredient', 'location', 'batch_number']]
        ordering = ['expiration_date', 'created_at']
    
    def __str__(self):
        batch_info = f" (Batch: {self.batch_number})" if self.batch_number else ""
        return f"{self.ingredient.name} at {self.location.name}: {self.quantity} {self.ingredient.unit}{batch_info}"
    
    @property
    def is_low_stock(self):
        """Check if this stock is below ingredient's reorder level"""
        return self.quantity < self.ingredient.reorder_level
    
    @property
    def is_expiring_soon(self):
        """Check if stock expires within 7 days"""
        if not self.expiration_date:
            return False
        return (self.expiration_date - timezone.now().date()).days <= 7
    
    @property
    def is_expired(self):
        """Check if stock is already expired"""
        if not self.expiration_date:
            return False
        return self.expiration_date < timezone.now().date()


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('WASTE', 'Waste'),
        ('TRANSFER', 'Transfer'),
        ('ADJUSTMENT', 'Adjustment'),
    ]
    
    stock = models.ForeignKey(
        Stock, 
        on_delete=models.PROTECT,
        related_name='movements'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Quantity moved (positive for IN, negative for OUT/WASTE)"
    )
    quantity_before = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Stock quantity before this movement"
    )
    quantity_after = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Stock quantity after this movement"
    )
    reason = models.TextField(help_text="Reason for this stock movement")
    reference = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Reference number (e.g., order ID, production batch)"
    )
    created_by = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT,
        related_name='stock_movements'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'inventory_stock_movement'
        indexes = [
            models.Index(fields=['stock', 'created_at']),
            models.Index(fields=['movement_type', 'created_at']),
            models.Index(fields=['created_by', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_movement_type_display()}: {abs(self.quantity)} {self.stock.ingredient.unit} - {self.reason[:50]}"
    
    @property
    def is_positive_movement(self):
        """Check if this movement increases stock"""
        return self.movement_type in ['IN']
