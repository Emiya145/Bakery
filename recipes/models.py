from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum, F


class Recipe(models.Model):
    product = models.ForeignKey(
        'products.Product', 
        on_delete=models.CASCADE,
        related_name='recipes'
    )
    yield_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Quantity of product this recipe yields"
    )
    yield_unit = models.CharField(
        max_length=20,
        help_text="Unit of the yield (should match product unit)"
    )
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    instructions = models.TextField(
        blank=True,
        help_text="Step-by-step instructions for making this recipe"
    )
    prep_time_minutes = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Preparation time in minutes"
    )
    cook_time_minutes = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Cooking time in minutes"
    )
    created_by = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT,
        related_name='created_recipes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recipes_recipe'
        ordering = ['-created_at']
        unique_together = [['product', 'version']]
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - v{self.version} ({self.yield_quantity} {self.yield_unit})"
    
    def calculate_total_cost(self):
        """Calculate total cost of ingredients for this recipe"""
        total_cost = 0
        for recipe_ingredient in self.ingredients.select_related('ingredient').all():
            if recipe_ingredient.ingredient.cost_per_unit:
                ingredient_cost = recipe_ingredient.quantity * recipe_ingredient.ingredient.cost_per_unit
                total_cost += ingredient_cost
        return total_cost
    
    def calculate_cost_per_unit(self):
        """Calculate cost per unit of product"""
        if self.yield_quantity > 0:
            return self.calculate_total_cost() / self.yield_quantity
        return 0
    
    def get_ingredient_summary(self):
        """Get a summary of all ingredients with quantities"""
        return self.ingredients.select_related('ingredient').all()
    
    def activate(self):
        """Activate this recipe and deactivate others for the same product"""
        Recipe.objects.filter(product=self.product).update(is_active=False)
        self.is_active = True
        self.save(update_fields=['is_active'])
    
    def create_new_version(self):
        """Create a new version of this recipe (copy current ingredients)"""
        new_version = self.version + 1
        
        # Create new recipe
        new_recipe = Recipe.objects.create(
            product=self.product,
            yield_quantity=self.yield_quantity,
            yield_unit=self.yield_unit,
            version=new_version,
            instructions=self.instructions,
            prep_time_minutes=self.prep_time_minutes,
            cook_time_minutes=self.cook_time_minutes,
            created_by=self.created_by
        )
        
        # Copy ingredients
        for recipe_ingredient in self.ingredients.all():
            RecipeIngredient.objects.create(
                recipe=new_recipe,
                ingredient=recipe_ingredient.ingredient,
                quantity=recipe_ingredient.quantity,
                optional=recipe_ingredient.optional
            )
        
        return new_recipe


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, 
        related_name='ingredients', 
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        'inventory.Ingredient', 
        on_delete=models.PROTECT,
        related_name='recipe_ingredients'
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Quantity of ingredient needed for the recipe yield"
    )
    optional = models.BooleanField(
        default=False,
        help_text="Whether this ingredient is optional"
    )
    notes = models.CharField(
        max_length=200,
        blank=True,
        help_text="Special notes about this ingredient"
    )
    
    class Meta:
        db_table = 'recipes_recipe_ingredient'
        unique_together = [['recipe', 'ingredient']]
        ordering = ['ingredient__name']
    
    def __str__(self):
        optional_text = " (optional)" if self.optional else ""
        return f"{self.ingredient.name}: {self.quantity} {self.ingredient.ingredient.unit}{optional_text}"
    
    @property
    def cost(self):
        """Calculate cost of this ingredient in the recipe"""
        if self.ingredient.cost_per_unit:
            return self.quantity * self.ingredient.cost_per_unit
        return 0


class ProductionBatch(models.Model):
    """
    Tracks production batches for audit trail and quality control
    """
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    recipe = models.ForeignKey(
        Recipe, 
        on_delete=models.PROTECT,
        related_name='production_batches'
    )
    quantity_produced = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Actual quantity produced"
    )
    location = models.ForeignKey(
        'inventory.Location', 
        on_delete=models.PROTECT,
        related_name='production_batches'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='PLANNED'
    )
    batch_number = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Unique batch number for traceability"
    )
    production_date = models.DateField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT,
        related_name='production_batches'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recipes_production_batch'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipe', 'production_date']),
            models.Index(fields=['status', 'production_date']),
            models.Index(fields=['batch_number']),
        ]
    
    def __str__(self):
        return f"Batch {self.batch_number}: {self.recipe.product.name} x{self.quantity_produced}"
    
    def calculate_ingredient_requirements(self):
        """Calculate required ingredients for this batch"""
        requirements = []
        for recipe_ingredient in self.recipe.ingredients.all():
            required_qty = recipe_ingredient.quantity * self.quantity_produced
            requirements.append({
                'ingredient': recipe_ingredient.ingredient,
                'required_quantity': required_qty,
                'unit': recipe_ingredient.ingredient.unit,
                'optional': recipe_ingredient.optional
            })
        return requirements
    
    def check_stock_availability(self):
        """Check if all required ingredients are available in sufficient quantity"""
        from inventory.models import Stock
        from django.db.models import Sum
        
        issues = []
        
        for recipe_ingredient in self.recipe.ingredients.all():
            if recipe_ingredient.optional:
                continue
                
            required_qty = recipe_ingredient.quantity * self.quantity_produced
            
            # Check total available stock at the production location
            available_stock = Stock.objects.filter(
                ingredient=recipe_ingredient.ingredient,
                location=self.location,
                quantity__gt=0
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            if available_stock < required_qty:
                issues.append({
                    'ingredient': recipe_ingredient.ingredient,
                    'required': required_qty,
                    'available': available_stock,
                    'shortage': required_qty - available_stock
                })
        
        return issues
