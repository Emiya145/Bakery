from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('STAFF', 'Staff'),
    ]
    
    role = models.CharField(
        max_length=20, 
        choices=ROLES, 
        default='STAFF',
        help_text="User role determines permissions"
    )
    location = models.ForeignKey(
        'inventory.Location', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        help_text="Primary location for staff users"
    )
    phone = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Contact phone number"
    )
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        return self.role == 'ADMIN'
    
    @property
    def is_manager(self):
        return self.role in ['ADMIN', 'MANAGER']
    
    @property
    def is_staff_or_above(self):
        return self.role in ['ADMIN', 'MANAGER', 'STAFF']
