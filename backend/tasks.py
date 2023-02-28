from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created
from rest_framework import status
from rest_framework.response import Response

from apiorders import settings
from backend.models import CustomUser, Order, ConfirmEmailToken, Supplier, ProductCategory, ProductSupplier, Product, \
    Parameter, ProductSupplierParameter


def get_order_info(order_id):
    order = Order.objects.get(id=order_id)
    order_sum = 0
    order_info: {}
    order_items = []
    for item in order.order_items.all():
        product_supplier = item.product_supplier
        product = product_supplier.product
        name = product.name
        quantity = item.quantity
        price = product_supplier.price
        item_sum = price * quantity
        order_sum += item_sum
        order_items.append({'product_supplier': product_supplier,
                            'product': product,
                            'name': product.name,
                            'quantity': quantity,
                            'price': price,
                            'sum': item_sum,
                            })
    return {'id': order.id, 'buyer': order.buyer, 'state': order.state, 'order_sum': order_sum,'order_items': order_items}

@shared_task()
def send_email_new_order_task(order_id, user_email, admin_emails):
    """
    Отправка письма пользователю и админ(у/ам) при размещении заказa
    """

    data = get_order_info(order_id)
    order_items = '\n'.join([f'{i + 1}) {item["name"]}:\n    '
                             f'{item["quantity"]} шт. * {item["price"]} руб. = {item["sum"]} руб.'
                             for i, item in enumerate(data['order_items'])])
    msg_to_user = EmailMultiAlternatives(
        f'Успешное размещение заказа №{data["id"]}',
        f'Заказ №{data["id"]}, покупатель: {data["buyer"].name!r}, сумма заказа: {data["order_sum"]} руб.\n'
        f'Детали заказа:\n{order_items}',
        settings.SERVER_EMAIL,
        [user_email]
    )
    msg_to_user.send()

    msg_to_admin = EmailMultiAlternatives(
        f'Заказ №{data["id"]}, покупатель: {data["buyer"].id}, статус: {data["state"]}',
        f'Заказ №{data["id"]}, покупатель: {data["buyer"].id}, сумма заказа: {data["order_sum"]} руб.\n'
        f'Детали заказа:\n{order_items}',
        settings.SERVER_EMAIL,
        admin_emails
    )
    msg_to_admin.send()


@shared_task()
def send_email_user_register_task(user_id):
    """
    Отправка письма с токеном для подтверждения регистрации (email)
    """

    user = CustomUser.objects.get(id=user_id)
    token, _ = ConfirmEmailToken.objects.get_or_create(user=user)
    msg = EmailMultiAlternatives(
        'Токен подтверждения регистрации',
        token.email_token,
        settings.SERVER_EMAIL,
        [token.user.email]
    )
    msg.send()


@receiver(reset_password_token_created)
def password_reset_requested(sender, reset_password_token, **kwargs):
    """
    Перехват сигнала
    """

    email = reset_password_token.user.email
    token = reset_password_token.key
    send_email_password_reset_task.delay(email, token)


@shared_task()
def send_email_password_reset_task(email, token):
    """
    Отправка письма с токеном для сброса пароля
    """

    msg = EmailMultiAlternatives(
        'Токен для сброса пароля',
        token,
        settings.SERVER_EMAIL,
        [email]
    )
    msg.send()


@shared_task()
def do_import_task(supplier_id, file_url, y_data):

    with transaction.atomic():
        updated = Supplier.objects.filter(id=supplier_id, name=y_data.get('shop')).update(file_url=file_url)
        if not updated:
            return Response({'error': f"Нет поставщика с именем {y_data.get('shop')}"},
                            status=status.HTTP_400_BAD_REQUEST)

        y_categories = y_data.get('categories')
        if y_categories:
            for cat in y_categories:
                category_id = cat.get('id')
                category_name = cat.get('name')
                category, _ = ProductCategory.objects.get_or_create(id=category_id, name=category_name)
                category.suppliers.add(supplier_id)
                category.save()

        ProductSupplier.objects.filter(supplier_id=supplier_id).delete()

        y_products = y_data.get('goods')
        if y_products:
            for item in y_products:
                product, _ = Product.objects.get_or_create(name=item.get('name'),
                                                           category_id=item.get('category'))

                product_supplier, _ = ProductSupplier.objects.get_or_create(product_id=product.id,
                                                                            supplier_id=supplier_id,
                                                                            external_id=item.get('id'),
                                                                            model=item.get('model'),
                                                                            price=item.get('price'),
                                                                            price_rrc=item.get('price_rrc'),
                                                                            quantity=item.get('quantity')
                                                                            )
                parameters = item.get('parameters')
                if parameters:
                    for name, value in parameters.items():
                        parameter, _ = Parameter.objects.get_or_create(name=name)
                        ProductSupplierParameter.objects.update_or_create(product_supplier_id=product_supplier.id,
                                                                          parameter_id=parameter.id,
                                                                          defaults={'value': value})

