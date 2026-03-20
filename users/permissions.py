from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'


class IsManagerOrAdmin(permissions.BasePermission):
    """
    Allows access only to manager or admin users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['ADMIN', 'MANAGER']


class IsStaffOrAbove(permissions.BasePermission):
    """
    Allows read access to staff and above, write access to managers and above.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return request.user.role in ['STAFF', 'MANAGER', 'ADMIN']
        
        return request.user.role in ['MANAGER', 'ADMIN']


class IsLocationStaffOrAbove(permissions.BasePermission):
    """
    Allows staff to access only their location data, managers and admins can access all.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Managers and admins can access all locations
        if request.user.role in ['MANAGER', 'ADMIN']:
            return True
        
        # Staff can only access their own location
        if request.user.role == 'STAFF':
            # Check if the object has a location field
            if hasattr(obj, 'location'):
                return obj.location == request.user.location
            # For stock objects, check the stock location
            if hasattr(obj, 'stock') and hasattr(obj.stock, 'location'):
                return obj.stock.location == request.user.location
            if hasattr(obj, 'location'):
                return obj.location == request.user.location
        
        return False
