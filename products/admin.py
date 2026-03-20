from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import ProductCategory, Product, ProductStock


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'product_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


class ProductStockInline(admin.TabularInline):
    model = ProductStock
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['location', 'quantity', 'batch_number', 'production_date', 'expiration_date']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'unit', 'selling_price', 'cost_price', 
        'profit_margin', 'total_stock', 'is_active'
    ]
    list_filter = ['category', 'unit', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProductStockInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'unit', 'is_active')
        }),
        ('Pricing', {
            'fields': ('selling_price', 'cost_price')
        }),
        ('Details', {
            'fields': ('description', 'image')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['update_cost_prices', 'calculate_profit_margins']
    
    def total_stock(self, obj):
        total = ProductStock.objects.filter(product=obj).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        return f"{total} {obj.unit}"
    total_stock.short_description = 'Total Stock'
    
    def profit_margin(self, obj):
        margin = obj.profit_margin
        if margin is not None:
            if margin > 0:
                return format_html('<span style="color: green;">{:.1f}%</span>', margin)
            else:
                return format_html('<span style="color: red;">{:.1f}%</span>', margin)
        return '-'
    profit_margin.short_description = 'Profit Margin'
    
    def update_cost_prices(self, request, queryset):
        updated = 0
        for product in queryset:
            try:
                product.update_cost_price()
                updated += 1
            except Exception as e:
                self.message_user(request, f"Error updating {product.name}: {str(e)}", level='error')
        
        self.message_user(request, f"Updated cost prices for {updated} products.")
    
    update_cost_prices.short_description = "Update cost prices from recipes"
    
    def calculate_profit_margins(self, request, queryset):
        # This is already handled by the profit_margin property
        self.message_user(request, "Profit margins are calculated automatically. Check the list display.")


@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'location', 'quantity', 'batch_number', 
        'production_date', 'expiration_date', 'is_expiring_soon', 'is_expired'
    ]
    list_filter = [
        'location', 'product__category', 'expiration_date', 'production_date'
    ]
    search_fields = ['product__name', 'batch_number', 'location__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Stock Information', {
            'fields': ('product', 'location', 'quantity', 'batch_number')
        }),
        ('Dates', {
            'fields': ('production_date', 'expiration_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_expiring_soon(self, obj):
        if obj.is_expiring_soon and not obj.is_expired:
            return format_html('<span style="color: orange;">⚠️ Expires Soon</span>')
        return ''
    is_expiring_soon.short_description = 'Expiring Soon'
    
    def is_expired(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">❌ Expired</span>')
        return ''
    is_expired.short_description = 'Expired'
    
    def get_queryset(self, request):
        # Staff can only see stock from their location
        if request.user.role == 'STAFF':
            return super().get_queryset(request).filter(location=request.user.location)
        return super().get_queryset(request)
