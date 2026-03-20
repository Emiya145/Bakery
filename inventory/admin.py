from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Location, Ingredient, Stock, StockMovement
from .services import InventoryService


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone', 'is_active', 'total_ingredients', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'address']
    readonly_fields = ['created_at']
    
    def total_ingredients(self, obj):
        return obj.total_ingredients


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'reorder_level', 'total_stock', 'is_low_stock', 'is_active']
    list_filter = ['unit', 'is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'unit', 'is_active')
        }),
        ('Stock Management', {
            'fields': ('reorder_level', 'cost_per_unit')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_stock(self, obj):
        total = obj.get_total_stock()
        if total < obj.reorder_level:
            return format_html('<span style="color: red;">{}</span>', total)
        return total
    total_stock.short_description = 'Total Stock'
    
    def is_low_stock(self, obj):
        return obj.is_low_stock()
    is_low_stock.boolean = True
    is_low_stock.short_description = 'Low Stock'


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = ['created_at', 'created_by']
    fields = ['movement_type', 'quantity', 'quantity_before', 'quantity_after', 'reason', 'reference', 'created_at', 'created_by']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = [
        'ingredient', 'location', 'quantity', 'unit', 'expiration_date', 
        'batch_number', 'is_low_stock', 'is_expiring_soon', 'is_expired'
    ]
    list_filter = [
        'location', 'ingredient__unit', 'expiration_date', 'created_at'
    ]
    search_fields = ['ingredient__name', 'batch_number', 'location__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [StockMovementInline]
    
    fieldsets = (
        ('Stock Information', {
            'fields': ('ingredient', 'location', 'quantity', 'batch_number')
        }),
        ('Expiration', {
            'fields': ('expiration_date',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_waste', 'bulk_restock', 'transfer_stock']
    
    def unit(self, obj):
        return obj.ingredient.unit
    unit.short_description = 'Unit'
    
    def is_low_stock(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color: orange;">⚠️ Low</span>')
        return format_html('<span style="color: green;">✓ OK</span>')
    is_low_stock.short_description = 'Stock Status'
    
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
    
    def mark_as_waste(self, request, queryset):
        if request.POST.get('post'):
            service = InventoryService()
            wasted_count = 0
            errors = []
            
            for stock in queryset:
                try:
                    service.mark_as_waste(
                        stock=stock,
                        quantity=stock.quantity,  # Waste all stock
                        user=request.user,
                        reason="Bulk waste action from admin"
                    )
                    wasted_count += 1
                except Exception as e:
                    errors.append(f"{stock.ingredient.name}: {str(e)}")
            
            if wasted_count:
                self.message_user(request, f"Successfully marked {wasted_count} stock items as waste.")
            if errors:
                self.message_user(request, f"Errors occurred: {'; '.join(errors)}", level='error')
        else:
            from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
            selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
            return render(request, 'admin/inventory/confirm_waste.html', {
                'queryset': queryset,
                'action_checkbox_name': ACTION_CHECKBOX_NAME,
                'selected': selected,
            })
    
    mark_as_waste.short_description = "Mark selected items as waste"
    
    def bulk_restock(self, request, queryset):
        # This would typically redirect to a custom form
        self.message_user(request, "Bulk restocking requires a custom form. Please use the API or individual stock editing.")
    
    bulk_restock.short_description = "Bulk restock (requires custom form)"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'stock_info', 'movement_type', 'quantity', 'quantity_before', 
        'quantity_after', 'reason_short', 'reference', 'created_by', 'created_at'
    ]
    list_filter = [
        'movement_type', 'created_at', 'stock__location', 'stock__ingredient'
    ]
    search_fields = [
        'stock__ingredient__name', 'reason', 'reference', 'created_by__username'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Movement Information', {
            'fields': ('stock', 'movement_type', 'quantity')
        }),
        ('Quantities', {
            'fields': ('quantity_before', 'quantity_after')
        }),
        ('Details', {
            'fields': ('reason', 'reference', 'created_by')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def stock_info(self, obj):
        url = reverse('admin:inventory_stock_change', args=[obj.stock.id])
        return format_html(
            '<a href="{}">{} - {}</a>',
            url,
            obj.stock.ingredient.name,
            obj.stock.location.name
        )
    stock_info.short_description = 'Stock'
    
    def reason_short(self, obj):
        if len(obj.reason) > 50:
            return obj.reason[:50] + '...'
        return obj.reason
    reason_short.short_description = 'Reason'
    
    def get_queryset(self, request):
        # Staff can only see movements from their location
        if request.user.role == 'STAFF':
            return super().get_queryset(request).filter(stock__location=request.user.location)
        return super().get_queryset(request)
    
    def has_add_permission(self, request):
        # Only managers and admins can manually add movements
        return request.user.role in ['MANAGER', 'ADMIN']
