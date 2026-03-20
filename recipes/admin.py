from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum

from .models import Recipe, RecipeIngredient, ProductionBatch


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    fields = [
        'ingredient', 'quantity', 'optional', 'notes', 'cost_display'
    ]
    readonly_fields = ['cost_display']
    
    def cost_display(self, obj):
        if obj.cost:
            return f"${obj.cost:.2f}"
        return '-'
    cost_display.short_description = 'Cost'


class ProductionBatchInline(admin.TabularInline):
    model = ProductionBatch
    extra = 0
    readonly_fields = ['created_at', 'updated_at', 'stock_issues']
    fields = [
        'batch_number', 'quantity_produced', 'location', 'status', 
        'production_date', 'notes', 'stock_issues'
    ]
    
    def stock_issues(self, obj):
        issues = obj.check_stock_availability()
        if issues:
            issue_list = []
            for issue in issues:
                issue_list.append(
                    f"{issue['ingredient'].name}: Need {issue['required']}, "
                    f"Have {issue['available']}"
                )
            return format_html(
                '<span style="color: red;">{}</span>',
                '; '.join(issue_list)
            )
        return format_html('<span style="color: green;">✓ All ingredients available</span>')
    stock_issues.short_description = 'Stock Issues'


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'version', 'yield_info', 'is_active', 
        'total_cost', 'cost_per_unit', 'created_by', 'created_at'
    ]
    list_filter = [
        'is_active', 'product__category', 'created_at', 'created_by'
    ]
    search_fields = [
        'product__name', 'instructions'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'total_cost', 'cost_per_unit'
    ]
    inlines = [RecipeIngredientInline, ProductionBatchInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'yield_quantity', 'yield_unit', 'version', 'is_active')
        }),
        ('Timing', {
            'fields': ('prep_time_minutes', 'cook_time_minutes')
        }),
        ('Instructions', {
            'fields': ('instructions',)
        }),
        ('Cost Analysis', {
            'fields': ('total_cost', 'cost_per_unit'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_recipe', 'create_new_version', 'update_product_costs']
    
    def yield_info(self, obj):
        return f"{obj.yield_quantity} {obj.yield_unit}"
    yield_info.short_description = 'Yield'
    
    def total_cost(self, obj):
        cost = obj.calculate_total_cost()
        if cost:
            return f"${cost:.2f}"
        return '-'
    total_cost.short_description = 'Total Cost'
    
    def cost_per_unit(self, obj):
        cost = obj.calculate_cost_per_unit()
        if cost:
            return f"${cost:.2f}"
        return '-'
    cost_per_unit.short_description = 'Cost/Unit'
    
    def get_queryset(self, request):
        # Staff can only see recipes for products they can access
        if request.user.role == 'STAFF':
            return super().get_queryset(request).filter(
                product__stock__location=request.user.location
            ).distinct()
        return super().get_queryset(request)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new recipe
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def activate_recipe(self, request, queryset):
        for recipe in queryset:
            recipe.activate()
        count = queryset.count()
        self.message_user(request, f"Activated {count} recipes and deactivated others.")
    
    activate_recipe.short_description = "Activate selected recipes"
    
    def create_new_version(self, request, queryset):
        created = 0
        for recipe in queryset:
            recipe.create_new_version()
            created += 1
        self.message_user(request, f"Created {created} new recipe versions.")
    
    create_new_version.short_description = "Create new version of selected recipes"
    
    def update_product_costs(self, request, queryset):
        updated = 0
        products_updated = set()
        for recipe in queryset:
            try:
                recipe.product.update_cost_price()
                products_updated.add(recipe.product.name)
                updated += 1
            except Exception as e:
                self.message_user(request, f"Error updating {recipe.product.name}: {str(e)}", level='error')
        
        if products_updated:
            self.message_user(request, f"Updated costs for products: {', '.join(products_updated)}")
    
    update_product_costs.short_description = "Update product costs from selected recipes"


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = [
        'recipe', 'ingredient', 'quantity', 'unit', 'optional', 'cost'
    ]
    list_filter = [
        'optional', 'recipe__product__category', 'ingredient__unit'
    ]
    search_fields = [
        'recipe__product__name', 'ingredient__name', 'notes'
    ]
    
    def unit(self, obj):
        return obj.ingredient.unit
    unit.short_description = 'Unit'
    
    def cost(self, obj):
        if obj.cost:
            return f"${obj.cost:.2f}"
        return '-'
    cost.short_description = 'Cost'


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = [
        'batch_number', 'recipe_product', 'quantity_produced', 
        'location', 'status', 'production_date', 'stock_status', 'created_by'
    ]
    list_filter = [
        'status', 'location', 'production_date', 'recipe__product__category'
    ]
    search_fields = [
        'batch_number', 'recipe__product__name', 'notes'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_number', 'recipe', 'quantity_produced', 'location')
        }),
        ('Status', {
            'fields': ('status', 'production_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['check_stock_availability', 'mark_as_completed', 'start_production']
    
    def recipe_product(self, obj):
        url = reverse('admin:recipes_recipe_change', args=[obj.recipe.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.recipe.product.name
        )
    recipe_product.short_description = 'Product'
    
    def stock_status(self, obj):
        issues = obj.check_stock_availability()
        if issues:
            return format_html(
                '<span style="color: red;">⚠️ {} issues</span>',
                len(issues)
            )
        return format_html('<span style="color: green;">✓ Available</span>')
    stock_status.short_description = 'Stock Status'
    
    def get_queryset(self, request):
        # Staff can only see batches from their location
        if request.user.role == 'STAFF':
            return super().get_queryset(request).filter(location=request.user.location)
        return super().get_queryset(request)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new batch
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def check_stock_availability(self, request, queryset):
        for batch in queryset:
            issues = batch.check_stock_availability()
            if issues:
                issue_list = []
                for issue in issues:
                    issue_list.append(
                        f"{issue['ingredient'].name}: Need {issue['required']}, "
                        f"Have {issue['available']} (Short: {issue['shortage']})"
                    )
                self.message_user(
                    request, 
                    f"Batch {batch.batch_number} has stock issues: {'; '.join(issue_list)}",
                    level='warning'
                )
            else:
                self.message_user(
                    request, 
                    f"Batch {batch.batch_number} has all required ingredients available."
                )
    
    check_stock_availability.short_description = "Check stock availability"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status__in=['PLANNED', 'IN_PROGRESS']).update(status='COMPLETED')
        self.message_user(request, f"Marked {updated} batches as completed.")
    
    mark_as_completed.short_description = "Mark selected batches as completed"
    
    def start_production(self, request, queryset):
        updated = queryset.filter(status='PLANNED').update(status='IN_PROGRESS')
        self.message_user(request, f"Started production for {updated} batches.")
    
    start_production.short_description = "Start production for selected batches"
