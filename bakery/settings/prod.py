"""
Production settings for bakery inventory system (PythonAnywhere).
"""
from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']

# Database - MySQL for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': 'yourusername.mysql.pythonanywhere-services.com',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Static files for PythonAnywhere
STATIC_ROOT = '/home/yourusername/bakery/static'
MEDIA_ROOT = '/home/yourusername/bakery/media'

# Logging paths for PythonAnywhere
LOGGING['handlers']['file']['filename'] = '/home/yourusername/logs/bakery.log'
LOGGING['handlers']['error_file']['filename'] = '/home/yourusername/logs/errors.log'

# CORS settings for production
CORS_ALLOWED_ORIGINS = [
    "https://yourusername.pythonanywhere.com",
]

# Email configuration for production
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@bakery.com')
