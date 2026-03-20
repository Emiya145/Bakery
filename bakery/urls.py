"""
URL configuration for bakery project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from inventory.views import (
    LocationViewSet, IngredientViewSet, StockViewSet,
    StockMovementViewSet, ProductionViewSet
)

# Create a single router for all API endpoints
router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='stockmovement')
router.register(r'production', ProductionViewSet, basename='production')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
