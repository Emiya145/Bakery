"""
URL configuration for bakery project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from .spa_views import spa_index
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as auth_views
from inventory.views import (
    LocationViewSet, IngredientViewSet, StockViewSet,
    StockMovementViewSet, ProductionViewSet
)
from users.views import UserViewSet, CurrentUserView

# Create a single router for all API endpoints
router = DefaultRouter()
router.include_format_suffixes = False
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='stockmovement')
router.register(r'production', ProductionViewSet, basename='production')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/login/', auth_views.obtain_auth_token),
    path('api/auth/me/', CurrentUserView.as_view()),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Production: React SPA (Vite build); /static/ is usually served by the web host (e.g. PythonAnywhere).
    urlpatterns += [
        path('', spa_index),
        path('<path:path>', spa_index),
    ]
