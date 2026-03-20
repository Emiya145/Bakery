from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LocationViewSet, IngredientViewSet, StockViewSet,
    StockMovementViewSet, ProductionViewSet
)

router = DefaultRouter(trailing_slash=False)
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='stockmovement')
router.register(r'production', ProductionViewSet, basename='production')

urlpatterns = router.urls
