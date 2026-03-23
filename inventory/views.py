from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Sum, Q, F

from .models import Location, Ingredient, Stock, StockMovement
from .serializers import (
    LocationSerializer, IngredientSerializer, StockSerializer,
    StockMovementSerializer, ProductionRequestSerializer,
    StockAdjustmentSerializer, WasteReportSerializer
)
from .services import InventoryService, InsufficientStockError
from users.permissions import IsManagerOrAdmin, IsStaffOrAbove


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['unit', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'reorder_level', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock')
        if low_stock and low_stock.lower() == 'true':
            low_stock_ids = []
            for ingredient in queryset:
                if ingredient.is_low_stock():
                    low_stock_ids.append(ingredient.id)
            queryset = queryset.filter(id__in=low_stock_ids)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def stock_history(self, request, pk=None):
        """Get stock movement history for an ingredient"""
        ingredient = self.get_object()
        movements = StockMovement.objects.filter(
            stock__ingredient=ingredient
        ).select_related('stock', 'created_by').order_by('-created_at')[:50]
        
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.select_related('ingredient', 'location').all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['ingredient', 'location']
    ordering_fields = ['expiration_date', 'quantity', 'created_at']
    ordering = ['expiration_date', 'created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock')
        if low_stock and low_stock.lower() == 'true':
            queryset = queryset.filter(
                quantity__lt=F('ingredient__reorder_level')
            )
        
        # Filter by expiring soon
        expiring_soon = self.request.query_params.get('expiring_soon')
        if expiring_soon and expiring_soon.lower() == 'true':
            from django.utils import timezone
            from datetime import timedelta
            threshold = timezone.now().date() + timedelta(days=7)
            queryset = queryset.filter(
                expiration_date__lte=threshold,
                expiration_date__gte=timezone.now().date(),
                quantity__gt=0
            )
        
        # Filter by expired
        expired = self.request.query_params.get('expired')
        if expired and expired.lower() == 'true':
            from django.utils import timezone
            queryset = queryset.filter(
                expiration_date__lt=timezone.now().date(),
                quantity__gt=0
            )
        
        return queryset
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsManagerOrAdmin])
    def adjust(self, request):
        """Adjust stock quantity"""
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        stock = serializer.validated_data['stock_id']
        new_quantity = serializer.validated_data['new_quantity']
        reason = serializer.validated_data['reason']
        
        service = InventoryService()
        try:
            movement = service.adjust_stock(
                stock=stock,
                new_quantity=new_quantity,
                user=request.user,
                reason=reason
            )
            return Response({
                'status': 'success',
                'message': f'Stock adjusted from {movement.quantity_before} to {movement.quantity_after}',
                'movement': StockMovementSerializer(movement).data
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsStaffOrAbove])
    def report_waste(self, request):
        """Report waste/spoilage"""
        serializer = WasteReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        stock = serializer.validated_data['stock_id']
        quantity = serializer.validated_data['quantity']
        reason = serializer.validated_data['reason']
        
        service = InventoryService()
        try:
            movement = service.mark_as_waste(
                stock=stock,
                quantity=quantity,
                user=request.user,
                reason=reason
            )
            return Response({
                'status': 'success',
                'message': f'Waste reported: {quantity} {stock.ingredient.unit}',
                'movement': StockMovementSerializer(movement).data
            })
        except InsufficientStockError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for stock movements (audit trail)"""
    queryset = StockMovement.objects.select_related(
        'stock__ingredient', 'stock__location', 'created_by'
    ).all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'stock__ingredient', 'stock__location', 'created_by']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset


class ProductionViewSet(viewsets.ViewSet):
    """ViewSet for production operations"""
    permission_classes = [IsAuthenticated, IsStaffOrAbove]
    
    @action(detail=False, methods=['post'])
    def produce(self, request):
        """Produce items and deduct ingredients"""
        serializer = ProductionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        recipe = serializer.validated_data['recipe']
        quantity = serializer.validated_data['quantity']
        location = serializer.validated_data['location']
        
        service = InventoryService()
        try:
            movements = service.deduct_for_production(
                recipe=recipe,
                quantity_produced=quantity,
                location=location,
                user=request.user
            )
            
            return Response({
                'status': 'success',
                'message': f'Produced {quantity} {recipe.product.name}',
                'deductions': [
                    {
                        'ingredient': m.stock.ingredient.name,
                        'quantity_used': m.quantity,
                        'unit': m.stock.ingredient.unit,
                        'batch': m.stock.batch_number
                    }
                    for m in movements
                ]
            })
        except InsufficientStockError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Production failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
