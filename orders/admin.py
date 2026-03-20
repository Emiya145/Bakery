from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, F

from .models import Customer, CustomerOrder, CustomerOrderItem


class CustomerOrderItemInline(admin.TabularInline):
    model = CustomerOrderItem
    extra = 1
    readonly_fields = ['total_price', 'cost_price', 'profit', 'profit_margin']
    fields = [
        'product', 'quantity', 'unit_price', 'total_price',
        'cost_price', 'profit', 'profit_margin', 'notes'
    ]
    
    def total_price(self, obj):
        if obj.total_price:
            return f"${obj.total_price:.2f}"
        return '-'
    total_price.short_description = 'Total'
    
    def cost_price(self, obj):
        if obj.cost_price:
            return f"${obj.cost_price:.2f}"
        return '-'
    cost_price.short_description = 'Cost'
    
    def profit(self, obj):
        profit = obj.profit
        if profit > 0:
            return format_html('<span style="color: green;">${:.2f}</span>', profit)
        elif profit < 0:
            return format_html('<span style="color: red;">${:.2f}</span>', profit)
        return '$0.00'
    profit.short_description = 'Profit'
    
    def profit_margin(self, obj):
        margin = obj.profit_margin
        if margin > 0:
            return format_html('<span style="color: green;">{:.1f}%</span>', margin)
        elif margin < 0:
            return format_html('<span style="color: red;">{:.1f}%</span>', margin)
        return '0.0%'
    profit_margin.short_description = 'Margin'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'phone', 'company', 'order_count', 
        'total_value', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'phone', 'company']
    readonly_fields = ['created_at', 'updated_at', 'order_count', 'total_value']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'phone', 'company')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Analytics', {
            'fields': ('order_count', 'total_value'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def order_count(self, obj):
        return obj.get_order_count()
    order_count.short_description = 'Orders'
    
    def total_value(self, obj):
        total = obj.get_total_orders_value()
        if total:
            return f"${total:.2f}"
        return '$0.00'
    total_value.short_description = 'Total Value'


@admin.register(CustomerOrder)
class CustomerOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer', 'status', 'priority', 'order_date',
        'requested_delivery_date', 'total_amount', 'items_count', 'production_status'
    ]
    list_filter = [
        'status', 'priority', 'customer', 'order_date', 'requested_delivery_date'
    ]
    search_fields = [
        'order_number', 'customer__name', 'notes'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'calculated_total', 'production_status'
    ]
    inlines = [CustomerOrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'status', 'priority')
        }),
        ('Dates', {
            'fields': ('order_date', 'requested_delivery_date', 'actual_delivery_date')
        }),
        ('Financial', {
            'fields': ('total_amount', 'discount_amount', 'discount_percentage', 'calculated_total')
        }),
        ('Production', {
            'fields': ('production_status',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'internal_notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'confirm_orders', 'start_production', 'mark_as_ready', 
        'complete_orders', 'cancel_orders'
    ]
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'
    
    def calculated_total(self, obj):
        calculated = obj.calculate_subtotal()
        if calculated != obj.total_amount:
            return format_html(
                '<span style="color: orange;">${:.2f} (recalculate)</span>',
                calculated
            )
        return f"${calculated:.2f}"
    calculated_total.short_description = 'Calculated Total'
    
    def production_status(self, obj):
        if obj.status in ['DRAFT', 'CANCELLED']:
            return '-'
        
        can_produce, message = obj.can_be_produced()
        if can_produce:
            return format_html('<span style="color: green;">✓ Ready</span>')
        else:
            return format_html('<span style="color: red;">⚠️ {}</span>', message[:30])
    production_status.short_description = 'Production Ready'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new order
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def confirm_orders(self, request, queryset):
        updated = queryset.filter(status='DRAFT').update(status='CONFIRMED')
        self.message_user(request, f"Confirmed {updated} orders.")
    
    confirm_orders.short_description = "Confirm selected orders"
    
    def start_production(self, request, queryset):
        started = 0
        errors = []
        
        for order in queryset.filter(status='CONFIRMED'):
            success, message = order.start_production(user=request.user)
            if success:
                started += 1
            else:
                errors.append(f"{order.order_number}: {message}")
        
        if started:
            self.message_user(request, f"Started production for {started} orders.")
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", level='error')
    
    start_production.short_description = "Start production for selected orders"
    
    def mark_as_ready(self, request, queryset):
        updated = queryset.filter(status='IN_PROGRESS').update(status='READY')
        self.message_user(request, f"Marked {updated} orders as ready for pickup.")
    
    mark_as_ready.short_description = "Mark as ready for pickup"
    
    def complete_orders(self, request, queryset):
        completed = 0
        for order in queryset.filter(status__in=['READY', 'IN_PROGRESS']):
            order.mark_as_completed(user=request.user)
            completed += 1
        self.message_user(request, f"Completed {completed} orders.")
    
    complete_orders.short_description = "Complete selected orders"
    
    def cancel_orders(self, request, queryset):
        updated = queryset.filter(status__in=['DRAFT', 'CONFIRMED']).update(status='CANCELLED')
        self.message_user(request, f"Cancelled {updated} orders.")
    
    cancel_orders.short_description = "Cancel selected orders"


@admin.register(CustomerOrderItem)
class CustomerOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'product', 'quantity', 'unit_price', 'total_price',
        'cost_price', 'profit', 'profit_margin'
    ]
    list_filter = [
        'order__customer', 'order__status', 'product__category'
    ]
    search_fields = [
        'order__order_number', 'product__name', 'notes'
    ]
    
    def total_price(self, obj):
        if obj.total_price:
            return f"${obj.total_price:.2f}"
        return '-'
    total_price.short_description = 'Total Price'
    
    def cost_price(self, obj):
        if obj.cost_price:
            return f"${obj.cost_price:.2f}"
        return '-'
    cost_price.short_description = 'Cost Price'
    
    def profit(self, obj):
        profit = obj.profit
        if profit > 0:
            return format_html('<span style="color: green;">${:.2f}</span>', profit)
        elif profit < 0:
            return format_html('<span style="color: red;">${:.2f}</span>', profit)
        return '$0.00'
    profit.short_description = 'Profit'
    
    def profit_margin(self, obj):
        margin = obj.profit_margin
        if margin > 0:
            return format_html('<span style="color: green;">{:.1f}%</span>', margin)
        elif margin < 0:
            return format_html('<span style="color: red;">{:.1f}%</span>', margin)
        return '0.0%'
    profit_margin.short_description = 'Profit Margin'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'product')
