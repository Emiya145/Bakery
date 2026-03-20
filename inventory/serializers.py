from rest_framework import serializers
from django.db.models import Sum
from .models import Location, Ingredient, Stock, StockMovement


class LocationSerializer(serializers.ModelSerializer):
    total_ingredients = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'phone', 'is_active', 'total_ingredients', 'created_at']
        read_only_fields = ['created_at']


class IngredientSerializer(serializers.ModelSerializer):
    total_stock = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    stock_by_location = serializers.SerializerMethodField()
    
    class Meta:
        model = Ingredient
        fields = [
            'id', 'name', 'unit', 'reorder_level', 'cost_per_unit',
            'is_active', 'total_stock', 'is_low_stock', 'stock_by_location',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_stock(self, obj):
        return obj.get_total_stock()
    
    def get_is_low_stock(self, obj):
        return obj.is_low_stock()
    
    def get_stock_by_location(self, obj):
        stocks = obj.stock_set.select_related('location').all()
        return [
            {
                'location_id': stock.location.id,
                'location_name': stock.location.name,
                'quantity': stock.quantity,
                'batch_number': stock.batch_number,
                'expiration_date': stock.expiration_date
            }
            for stock in stocks if stock.quantity > 0
        ]


class StockSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Stock
        fields = [
            'id', 'ingredient', 'ingredient_name', 'ingredient_unit',
            'location', 'location_name', 'quantity', 'expiration_date',
            'batch_number', 'is_low_stock', 'is_expiring_soon', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='stock.ingredient.name', read_only=True)
    location_name = serializers.CharField(source='stock.location.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'stock', 'ingredient_name', 'location_name',
            'movement_type', 'movement_type_display', 'quantity',
            'quantity_before', 'quantity_after', 'reason', 'reference',
            'created_by', 'created_by_username', 'created_at'
        ]
        read_only_fields = ['quantity_before', 'quantity_after', 'created_at']


class ProductionRequestSerializer(serializers.Serializer):
    """Serializer for production requests"""
    recipe_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    location_id = serializers.IntegerField()
    
    def validate(self, data):
        from recipes.models import Recipe
        
        # Validate recipe exists
        try:
            recipe = Recipe.objects.get(id=data['recipe_id'], is_active=True)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Recipe not found or not active")
        
        # Validate location exists
        try:
            location = Location.objects.get(id=data['location_id'], is_active=True)
        except Location.DoesNotExist:
            raise serializers.ValidationError("Location not found or not active")
        
        data['recipe'] = recipe
        data['location'] = location
        return data


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer for stock adjustments"""
    stock_id = serializers.IntegerField()
    new_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    reason = serializers.CharField(max_length=500)
    
    def validate_stock_id(self, value):
        try:
            stock = Stock.objects.get(id=value)
            return stock
        except Stock.DoesNotExist:
            raise serializers.ValidationError("Stock not found")


class WasteReportSerializer(serializers.Serializer):
    """Serializer for waste reporting"""
    stock_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    reason = serializers.CharField(max_length=500)
    
    def validate_stock_id(self, value):
        try:
            stock = Stock.objects.get(id=value)
            return stock
        except Stock.DoesNotExist:
            raise serializers.ValidationError("Stock not found")
