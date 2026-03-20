from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as auth_views

from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', auth_views.obtain_auth_token),
    path('auth/me/', views.CurrentUserView.as_view()),
]
