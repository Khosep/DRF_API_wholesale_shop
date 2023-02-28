from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import ConfirmEmailToken, CustomUser


user_registered = Signal()
new_orders_to_user = Signal()
new_orders_to_admin = Signal()



@receiver(user_registered)
def user_registered_signal(instance, **kwargs):
    """
    Отправка письма с токеном для подтверждения регистрации (email)
    """
    token, _ = ConfirmEmailToken.objects.get_or_create(user=instance)
    msg = EmailMultiAlternatives(
        # subject:
        'Токен подтверждения регистрации',
        # message:
        token.email_token,
        # from:
        settings.SERVER_EMAIL,
        # to:
        [token.user.email]
    )
    msg.send()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправка письма с токеном для сброса пароля
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param kwargs:
    :return:
    """

    msg = EmailMultiAlternatives(
        'Токен для сброса пароля',
        reset_password_token.key,
        settings.SERVER_EMAIL,
        [reset_password_token.user.email]
    )
    msg.send()

def get_order_info(order):
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


@receiver(new_orders_to_user)
def new_orders_to_user_signal(user, orders, **kwargs):
    """
    Отправка письма пользователю при размещении заказ(а/ов)
    """
    for order in orders:
        data = get_order_info(order)
        admin_emails = [admin.email for admin in CustomUser.objects.filter(is_superuser=True, is_active=True)]

        order_items = '\n'.join([f'{i+1}) {item["name"]}:\n    '
                                 f'{item["quantity"]} шт. * {item["price"]} руб. = {item["sum"]} руб.'
                       for i, item in enumerate(data['order_items'])])

        msg_to_user = EmailMultiAlternatives(
            f'Успешное размещение заказа №{data["id"]}',
            f'Заказ №{data["id"]}, покупатель: {data["buyer"].name!r}, сумма заказа: {data["order_sum"]} руб.\n'
            f'Детали заказа:\n{order_items}',
            settings.SERVER_EMAIL,
            [user.email]
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


