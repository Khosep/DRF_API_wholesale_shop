from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from backend.models import CustomUser, Supplier, Buyer, ProductCategory, Product, ProductSupplier, Parameter, \
    ProductSupplierParameter, Order, OrderItem
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import Token, TokenProxy


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email',)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', )



class SupplierInline(admin.StackedInline):
    model = Supplier
    extra = 0


class BuyerInline(admin.StackedInline):
    model = Buyer
    extra = 0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = [SupplierInline, BuyerInline]
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ('id', 'email', 'first_name', 'last_name', 'company', 'position', 'type', 'is_active')
    list_filter = ('is_active', 'type')
    search_fields = ('company', 'first_name', 'last_name', 'email')
    ordering = ('-is_active', '-type', 'email',)
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return ((None, {'classes': ('wide',),
                            'fields': ('email', 'password1', 'password2')}),)
        return (
            (None, {'fields': ('email', 'password')}),
            ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position', 'type')}),
            ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
            ('Important dates', {'fields': ('last_login', 'date_joined')}),
        )

@admin.register(Token)
class CustomTokenAdmin(TokenAdmin):
    list_display = ('user', 'key', 'created')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'file_url', 'is_available', 'user')
    list_filter = ('is_available',)

@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'person', 'locality_name', 'user')

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'suppliers')

    def suppliers(self, obj):
        return ", ".join(sorted([str(s.id) for s in obj.suppliers.all()]))


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'state', 'buyer', 'created_at', 'updated_at')
    list_filter = ('state', 'updated_at')
    ordering = ('-state', 'updated_at',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_id', 'state', 'product_id', 'product', 'supplier', 'buyer', 'quantity', 'price', 'sum_item')
    ordering = ('id',)

    def price(self, obj):
        return f'{obj.product_supplier.price:,}'

    def sum_item(self, obj):
        return f'{obj.product_supplier.price * obj.quantity:,}'

    def buyer(self, obj):
        return obj.order.buyer

    def supplier(self, obj):
        return obj.product_supplier.supplier

    def product_id(self, obj):
        return obj.product_supplier.product.id

    def product(self, obj):
        return obj.product_supplier.product.name

    def order_id(self, obj):
        return obj.order.id

    def state(self, obj):
        return obj.order.state

@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'product', 'model', 'price', 'quantity', 'external_id')
    ordering = ('supplier', 'id',)

    def price(self, obj):
        return f'{obj.product_supplier.price:,}'



admin.site.unregister(TokenProxy)
admin.site.register(Product)
admin.site.register(Parameter)
