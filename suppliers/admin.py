from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, F

from .models import Supplier, SupplierPrice, SupplierOrder, SupplierOrderItem


class SupplierPriceInline(admin.TabularInline):
    model = SupplierPrice
    extra = 0
    readonly_fields = ['created_at', 'is_current']
    fields = [
        'ingredient', 'price_per_unit', 'unit', 'valid_from', 
        'valid_until', 'minimum_quantity', 'is_current', 'notes'
    ]
    
    def is_current(self, obj):
        if obj.is_current:
            return format_html('<span style="color: green;">✓ Current</span>')
        return format_html('<span style="color: gray;">Expired</span>')
    is_current.short_description = 'Current'


class SupplierOrderItemInline(admin.TabularInline):
    model = SupplierOrderItem
    extra = 1
    readonly_fields = ['total_price', 'is_fully_received', 'reception_variance']
    fields = [
        'ingredient', 'quantity', 'unit_price', 'total_price',
        'quantity_received', 'is_fully_received', 'reception_variance',
        'batch_number', 'expiration_date', 'notes'
    ]
    
    def total_price(self, obj):
        if obj.total_price:
            return f"${obj.total_price:.2f}"
        return '-'
    total_price.short_description = 'Total'
    
    def is_fully_received(self, obj):
        if obj.is_fully_received:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: orange;">⚠️ No</span>')
    is_fully_received.short_description = 'Received'
    
    def reception_variance(self, obj):
        variance = obj.reception_variance
        if variance is None:
            return '-'
        elif variance == 0:
            return format_html('<span style="color: green;">{}</span>', variance)
        elif variance > 0:
            return format_html('<span style="color: blue;">+{}</span>', variance)
        else:
            return format_html('<span style="color: red;">{}</span>', variance)
    reception_variance.short_description = 'Variance'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'contact_person', 'email', 'lead_time_days', 
        'active_products_count', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'lead_time_days', 'created_at']
    search_fields = ['name', 'contact_person', 'email']
    readonly_fields = ['created_at', 'updated_at', 'average_lead_time']
    inlines = [SupplierPriceInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'contact_person', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Order Terms', {
            'fields': ('lead_time_days', 'minimum_order_value', 'payment_terms')
        }),
        ('Analytics', {
            'fields': ('average_lead_time',),
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
    
    def active_products_count(self, obj):
        return obj.get_active_price_list().count()
    active_products_count.short_description = 'Active Products'
    
    def average_lead_time(self, obj):
        avg = obj.get_average_lead_time()
        if avg != obj.lead_time_days:
            return f"{avg:.1f} days (vs {obj.lead_time_days} standard)"
        return f"{avg:.1f} days"
    average_lead_time.short_description = 'Avg Lead Time'


@admin.register(SupplierPrice)
class SupplierPriceAdmin(admin.ModelAdmin):
    list_display = [
        'supplier', 'ingredient', 'price_per_unit', 'unit', 
        'valid_from', 'valid_until', 'is_current', 'minimum_quantity'
    ]
    list_filter = [
        'supplier', 'valid_from', 'valid_until', 'unit'
    ]
    search_fields = [
        'supplier__name', 'ingredient__name', 'notes'
    ]
    readonly_fields = ['created_at', 'is_current']
    
    fieldsets = (
        ('Price Information', {
            'fields': ('supplier', 'ingredient', 'price_per_unit', 'unit')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'is_current')
        }),
        ('Terms', {
            'fields': ('minimum_quantity', 'notes')
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def is_current(self, obj):
        if obj.is_current:
            return format_html('<span style="color: green;">✓ Current</span>')
        return format_html('<span style="color: gray;">Expired</span>')
    is_current.short_description = 'Current Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('supplier', 'ingredient')


class SupplierOrderItemInline(admin.TabularInline):
    model = SupplierOrderItem
    extra = 1
    readonly_fields = ['total_price']
    fields = [
        'ingredient', 'quantity', 'unit_price', 'total_price',
        'quantity_received', 'batch_number', 'expiration_date', 'notes'
    ]
    
    def total_price(self, obj):
        if obj.total_price:
            return f"${obj.total_price:.2f}"
        return '-'
    total_price.short_description = 'Total'


@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'supplier', 'status', 'order_date', 
        'expected_delivery_date', 'actual_delivery_date', 
        'total_amount', 'items_count', 'created_by'
    ]
    list_filter = [
        'status', 'supplier', 'order_date', 'expected_delivery_date'
    ]
    search_fields = [
        'order_number', 'supplier__name', 'notes'
    ]
    readonly_fields = ['created_at', 'updated_at', 'calculated_total']
    inlines = [SupplierOrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'supplier', 'status')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery_date', 'actual_delivery_date')
        }),
        ('Financial', {
            'fields': ('total_amount', 'calculated_total')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_sent', 'mark_as_confirmed', 'mark_as_shipped', 'mark_as_received']
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'
    
    def calculated_total(self, obj):
        calculated = obj.items.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0
        if calculated != obj.total_amount:
            return format_html(
                '<span style="color: orange;">${:.2f} (recalculate)</span>',
                calculated
            )
        return f"${calculated:.2f}"
    calculated_total.short_description = 'Calculated Total'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('supplier', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new order
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(status='DRAFT').update(status='SENT')
        self.message_user(request, f"Marked {updated} orders as sent to supplier.")
    
    mark_as_sent.short_description = "Mark as sent to supplier"
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.filter(status='SENT').update(status='CONFIRMED')
        self.message_user(request, f"Marked {updated} orders as confirmed by supplier.")
    
    mark_as_confirmed.short_description = "Mark as confirmed by supplier"
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.filter(status='CONFIRMED').update(status='SHIPPED')
        self.message_user(request, f"Marked {updated} orders as shipped.")
    
    mark_as_shipped.short_description = "Mark as shipped"
    
    def mark_as_received(self, request, queryset):
        from django.utils import timezone
        received_count = 0
        errors = []
        
        for order in queryset.filter(status__in=['SHIPPED', 'CONFIRMED']):
            try:
                order.mark_as_received(user=request.user, actual_date=timezone.now().date())
                received_count += 1
            except Exception as e:
                errors.append(f"{order.order_number}: {str(e)}")
        
        if received_count:
            self.message_user(request, f"Received {received_count} orders and updated stock.")
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", level='error')
    
    mark_as_received.short_description = "Mark as received (updates stock)"


@admin.register(SupplierOrderItem)
class SupplierOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'ingredient', 'quantity', 'unit_price', 'total_price',
        'quantity_received', 'reception_status'
    ]
    list_filter = [
        'order__supplier', 'order__status', 'ingredient'
    ]
    search_fields = [
        'order__order_number', 'ingredient__name', 'notes'
    ]
    
    def total_price(self, obj):
        if obj.total_price:
            return f"${obj.total_price:.2f}"
        return '-'
    total_price.short_description = 'Total Price'
    
    def reception_status(self, obj):
        if obj.quantity_received is None:
            return format_html('<span style="color: gray;">Pending</span>')
        elif obj.is_fully_received:
            return format_html('<span style="color: green;">✓ Full</span>')
        else:
            return format_html('<span style="color: orange;">⚠️ Partial ({})</span>', obj.quantity_received)
    reception_status.short_description = 'Reception'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'ingredient')
