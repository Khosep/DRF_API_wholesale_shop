from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_superuser


class IsBuyer(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.type == "buyer" or request.user.is_superuser


class IsSupplier(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.type == "supplier" or request.user.is_superuser


class IsSupplierOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user.is_authenticated and (request.user.type == "supplier" or request.user.is_superuser)
        )


class BuyerViewPermission(permissions.BasePermission):
    """Класс разрешений для BuyerViewSet"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if view.action == 'list':
            return request.user.type == "buyer" or request.user.is_superuser
        elif view.action == 'create':
            return request.user.type == "buyer" or request.user.is_superuser
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return (obj.user == request.user and request.user.type == "buyer") or request.user.is_superuser
        else:
            return False


class SupplierViewPermission(permissions.BasePermission):
    """Класс разрешений для SupplierViewSet"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            if view.action in ('list', 'retrieve'):
                return True
            else:
                return False
        if view.action == 'create':
            return (request.user.type == "supplier" or request.user.is_superuser) and request.user.is_authenticated
        elif view.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        if view.action == 'retrieve':
            return True
        elif not request.user.is_authenticated:
            return False
        elif view.action in ['update', 'partial_update', 'destroy']:
            return (obj.user == request.user and request.user.type == "supplier") or request.user.is_superuser
        else:
            return False


