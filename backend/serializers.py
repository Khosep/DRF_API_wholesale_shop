from rest_framework import serializers
from backend.models import *

class RegisterAccountSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'company', 'position', 'type')


class SupplierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'person', 'phone', 'file_url', 'is_available', 'user']
        read_only_fields = ('id', 'user')


class BuyerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Buyer
        fields = '__all__'
        read_only_fields = ('id', 'user')


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Для UserProfileView. В зависимости от значения поля "type" пользователя добавляет в
    fields дополнительное поле (если type="buyer" добавляет поле "buyers", для type="supplier" - "suppliers")
    """

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'company', 'position', 'type')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.type == 'buyer':
            data['buyers'] = BuyerSerializer(instance.buyers.all(), many=True).data
        elif instance.type == 'supplier':
            data['suppliers'] = SupplierSerializer(instance.suppliers.all(), many=True).data
        return data


class ProductCategorySerializer(serializers.ModelSerializer):

    suppliers = serializers.SerializerMethodField()

    # получает поставщиков только с доступными заказами (is_available=True), и всех - в строку
    def get_suppliers(self, obj):
        suppliers = obj.suppliers.filter(is_available=True)
        serializer = SupplierSerializer(suppliers, many=True)
        suppliers_view = ", ".join([supplier['name'] for supplier in serializer.data])
        return suppliers_view

    class Meta:
        model = ProductCategory
        fields = ('id', 'name', 'suppliers')


class PriceListUpdateSerializer(serializers.Serializer):

    supplier_id = serializers.IntegerField()
    file_url = serializers.URLField()


class ProductSerializer(serializers.ModelSerializer):

    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'category',)
        read_only_fields = ('id',)


class ProductSupplierSerializer(serializers.ModelSerializer):

    product = ProductSerializer(read_only=True)
    p_parameters = serializers.SerializerMethodField()

    def get_p_parameters(self, obj):
        parameters_view = [f'{param.parameter.name}: {param.value}' for param in obj.p_parameters.all()]
        return parameters_view

    class Meta:
        model = ProductSupplier
        fields = ('product', 'model', 'supplier', 'quantity', 'price', 'p_parameters',)
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product_supplier', 'quantity']
        read_only_fields = ['id']

    def create(self, validated_data):
        order = validated_data['order']
        product_supplier = validated_data['product_supplier']
        quantity = validated_data['quantity']
        instance, _ = OrderItem.objects.update_or_create(
            order=order,
            product_supplier=product_supplier,
            defaults={'quantity': quantity}
        )
        return instance


class OrderItemGetSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(max_length=150)
    sum = serializers.DecimalField(max_digits=11, decimal_places=2)
    external_id = serializers.IntegerField(required=False)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_supplier_id', 'product_name', 'external_id', 'quantity', 'sum']
        read_only_fields = ['id']


class BasketGetSerializer(serializers.Serializer):

    buyer_id = serializers.IntegerField()
    order_id = serializers.IntegerField()
    order_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    order_items = OrderItemGetSerializer(many=True)


class OrderSerializer(serializers.ModelSerializer):
    order_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    state = serializers.ChoiceField(choices=STATE_CHOICES[1:])
    order_items = OrderItemGetSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'buyer_id', 'state', 'order_sum', 'order_items']
        read_only_fields = ['id']

class BuyerOrderGetSerializer(serializers.Serializer):

    buyer_id = serializers.IntegerField()
    buyer_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders = OrderSerializer(many=True)

class BuyerOrderPostRequestSerializer(serializers.Serializer):

    orders_ids = serializers.ListField(child=serializers.IntegerField())


class SupplierOrdertGetSerializer(serializers.Serializer):

    supplier_id = serializers.IntegerField()
    supplier_sum = serializers.DecimalField(max_digits=12, decimal_places=2)
    # orders = serializers.ListField(child=serializers.DictField())
    orders = OrderSerializer(many=True)

# Блок из 2-х сериалайзеров для метода POST BasketView:
class BasketPostOrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    supplier_id = serializers.IntegerField()
    quantity = serializers.IntegerField()

class BasketPostRequestSerializer(serializers.Serializer):
    buyer_id = serializers.IntegerField()
    items = BasketPostOrderItemSerializer(many=True)


class BasketDeletetRequestSerializer(serializers.Serializer):
    buyer_id = serializers.IntegerField()
    items = serializers.ListField(child=serializers.IntegerField())





