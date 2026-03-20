from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

from .models import Stock, StockMovement, Ingredient, Location

logger = logging.getLogger('inventory')


class InsufficientStockError(Exception):
    """Raised when there's not enough stock for an operation"""
    pass


class InventoryService:
    """
    Service class for handling inventory operations with proper transaction management
    and race condition prevention.
    """
    
    @transaction.atomic
    def deduct_for_production(self, recipe, quantity_produced, location, user, reference=None):
        """
        Deduct ingredients when producing items.
        Uses select_for_update to prevent race conditions.
        
        Args:
            recipe: Recipe object
            quantity_produced: Decimal - quantity of product being produced
            location: Location object
            user: User object performing the operation
            reference: Optional reference string
            
        Returns:
            list: Created StockMovement objects
            
        Raises:
            InsufficientStockError: If not enough stock available
        """
        movements = []
        
        for recipe_ingredient in recipe.ingredients.select_related('ingredient').all():
            required_qty = recipe_ingredient.quantity * quantity_produced
            
            # Get all stock batches for this ingredient at this location
            # Order by expiration date (FIFO - First In, First Out)
            stock_batches = Stock.objects.select_for_update().filter(
                ingredient=recipe_ingredient.ingredient,
                location=location,
                quantity__gt=0
            ).order_by('expiration_date', 'created_at')
            
            if not stock_batches.exists():
                raise InsufficientStockError(
                    f"No stock available for {recipe_ingredient.ingredient.name} at {location.name}"
                )
            
            # Check total available quantity
            total_available = stock_batches.aggregate(total=Sum('quantity'))['total'] or 0
            if total_available < required_qty:
                raise InsufficientStockError(
                    f"Not enough {recipe_ingredient.ingredient.name} at {location.name}. "
                    f"Required: {required_qty} {recipe_ingredient.ingredient.unit}, "
                    f"Available: {total_available} {recipe_ingredient.ingredient.unit}"
                )
            
            # Deduct from batches using FIFO
            remaining_qty = required_qty
            for stock in stock_batches:
                if remaining_qty <= 0:
                    break
                
                qty_to_deduct = min(stock.quantity, remaining_qty)
                quantity_before = stock.quantity
                
                # Atomic update
                stock.quantity = F('quantity') - qty_to_deduct
                stock.save(update_fields=['quantity'])
                
                # Refresh to get updated quantity
                stock.refresh_from_db()
                quantity_after = stock.quantity
                
                # Create movement record
                movement = StockMovement.objects.create(
                    stock=stock,
                    movement_type='OUT',
                    quantity=qty_to_deduct,
                    quantity_before=quantity_before,
                    quantity_after=quantity_after,
                    reason=f"Production: {recipe.product.name} x{quantity_produced}",
                    reference=reference or f"PROD-{timezone.now().strftime('%Y%m%d%H%M')}",
                    created_by=user
                )
                movements.append(movement)
                
                remaining_qty -= qty_to_deduct
                
                logger.info(
                    f"Deducted {qty_to_deduct} {stock.ingredient.unit} of "
                    f"{stock.ingredient.name} from batch {stock.batch_number or 'N/A'} "
                    f"for production of {recipe.product.name}"
                )
        
        return movements
    
    @transaction.atomic
    def receive_supplier_order(self, order_items, location, user, reference=None):
        """
        Receive items from a supplier order.
        Creates or updates stock records with FIFO expiration tracking.
        
        Args:
            order_items: List of dicts with ingredient, quantity, batch_number, expiration_date
            location: Location object
            user: User object receiving the order
            reference: Optional reference string
            
        Returns:
            list: Created StockMovement objects
        """
        movements = []
        
        for item in order_items:
            ingredient = item['ingredient']
            quantity = item['quantity']
            batch_number = item.get('batch_number', '')
            expiration_date = item.get('expiration_date')
            
            # Get or create stock record
            stock, created = Stock.objects.get_or_create(
                ingredient=ingredient,
                location=location,
                batch_number=batch_number,
                defaults={
                    'quantity': 0,
                    'expiration_date': expiration_date
                }
            )
            
            # Update expiration date if provided and stock was created
            if created and expiration_date:
                stock.expiration_date = expiration_date
                stock.save()
            
            quantity_before = stock.quantity
            
            # Atomic update
            stock.quantity = F('quantity') + quantity
            stock.save(update_fields=['quantity'])
            
            # Refresh to get updated quantity
            stock.refresh_from_db()
            quantity_after = stock.quantity
            
            # Create movement record
            movement = StockMovement.objects.create(
                stock=stock,
                movement_type='IN',
                quantity=quantity,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=f"Supplier order received",
                reference=reference or f"PO-{timezone.now().strftime('%Y%m%d%H%M')}",
                created_by=user
            )
            movements.append(movement)
            
            logger.info(
                f"Added {quantity} {ingredient.unit} of {ingredient.name} "
                f"to stock at {location.name} (Batch: {batch_number or 'N/A'})"
            )
        
        return movements
    
    @transaction.atomic
    def transfer_stock(self, stock, quantity, to_location, user, reason=None):
        """
        Transfer stock from one location to another.
        
        Args:
            stock: Stock object to transfer from
            quantity: Decimal - quantity to transfer
            to_location: Location object to transfer to
            user: User object performing the transfer
            reason: Optional reason for transfer
            
        Returns:
            tuple: (from_movement, to_movement) StockMovement objects
            
        Raises:
            InsufficientStockError: If not enough stock to transfer
            ValidationError: If transferring to same location
        """
        if stock.location == to_location:
            raise ValidationError("Cannot transfer stock to the same location")
        
        if stock.quantity < quantity:
            raise InsufficientStockError(
                f"Not enough stock to transfer. Available: {stock.quantity}, Requested: {quantity}"
            )
        
        # Deduct from source location
        quantity_before = stock.quantity
        stock.quantity = F('quantity') - quantity
        stock.save(update_fields=['quantity'])
        stock.refresh_from_db()
        
        from_movement = StockMovement.objects.create(
            stock=stock,
            movement_type='TRANSFER',
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=stock.quantity,
            reason=reason or f"Transfer to {to_location.name}",
            created_by=user
        )
        
        # Add to destination location
        dest_stock, created = Stock.objects.get_or_create(
            ingredient=stock.ingredient,
            location=to_location,
            batch_number=stock.batch_number,
            defaults={
                'quantity': 0,
                'expiration_date': stock.expiration_date
            }
        )
        
        quantity_before_dest = dest_stock.quantity
        dest_stock.quantity = F('quantity') + quantity
        dest_stock.save(update_fields=['quantity'])
        dest_stock.refresh_from_db()
        
        to_movement = StockMovement.objects.create(
            stock=dest_stock,
            movement_type='TRANSFER',
            quantity=quantity,
            quantity_before=quantity_before_dest,
            quantity_after=dest_stock.quantity,
            reason=reason or f"Transfer from {stock.location.name}",
            created_by=user
        )
        
        logger.info(
            f"Transferred {quantity} {stock.ingredient.unit} of {stock.ingredient.name} "
            f"from {stock.location.name} to {to_location.name}"
        )
        
        return from_movement, to_movement
    
    @transaction.atomic
    def adjust_stock(self, stock, new_quantity, user, reason=None):
        """
        Adjust stock quantity (for inventory counts, corrections, etc.).
        
        Args:
            stock: Stock object to adjust
            new_quantity: Decimal - new stock quantity
            user: User object performing the adjustment
            reason: Reason for adjustment
            
        Returns:
            StockMovement: Created movement record
        """
        quantity_before = stock.quantity
        quantity_diff = new_quantity - quantity_before
        
        if quantity_diff == 0:
            raise ValidationError("No adjustment needed - quantity is the same")
        
        movement_type = 'ADJUSTMENT'
        quantity = abs(quantity_diff)
        
        # Update stock
        stock.quantity = new_quantity
        stock.save(update_fields=['quantity'])
        
        # Create movement record
        movement = StockMovement.objects.create(
            stock=stock,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=new_quantity,
            reason=reason or "Stock adjustment",
            created_by=user
        )
        
        logger.info(
            f"Adjusted {stock.ingredient.name} at {stock.location.name} "
            f"from {quantity_before} to {new_quantity} {stock.ingredient.unit}"
        )
        
        return movement
    
    @transaction.atomic
    def mark_as_waste(self, stock, quantity, user, reason=None):
        """
        Mark stock as waste/spoilage.
        
        Args:
            stock: Stock object to waste
            quantity: Decimal - quantity to waste
            user: User object performing the action
            reason: Reason for waste
            
        Returns:
            StockMovement: Created movement record
            
        Raises:
            InsufficientStockError: If not enough stock to waste
        """
        if stock.quantity < quantity:
            raise InsufficientStockError(
                f"Not enough stock to waste. Available: {stock.quantity}, Requested: {quantity}"
            )
        
        quantity_before = stock.quantity
        stock.quantity = F('quantity') - quantity
        stock.save(update_fields=['quantity'])
        stock.refresh_from_db()
        
        movement = StockMovement.objects.create(
            stock=stock,
            movement_type='WASTE',
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=stock.quantity,
            reason=reason or "Marked as waste/spoilage",
            created_by=user
        )
        
        logger.info(
            f"Wasted {quantity} {stock.ingredient.unit} of {stock.ingredient.name} "
            f"at {stock.location.name}"
        )
        
        return movement
