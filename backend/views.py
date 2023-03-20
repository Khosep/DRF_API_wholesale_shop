import requests
import yaml

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q, Sum, F
from drf_social_oauth2.views import ConvertTokenView
from drf_spectacular.utils import extend_schema
from rest_framework import generics, views, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.db import IntegrityError
from rest_framework.authentication import TokenAuthentication, BasicAuthentication, SessionAuthentication
from yaml import SafeLoader

from apiorders.schema import extend_schema_data
from backend.models import CustomUser, Buyer, ConfirmEmailToken, Supplier, ProductCategory, ProductSupplier, \
    Order, OrderItem
from backend.permissions import *
from backend.serializers import RegisterAccountSerializer, UserProfileSerializer, BuyerSerializer, SupplierSerializer, \
    ProductCategorySerializer, PriceListUpdateSerializer, ProductSupplierSerializer, OrderItemSerializer, \
    BasketGetSerializer, BuyerOrderGetSerializer, SupplierOrdertGetSerializer, BasketPostRequestSerializer, \
    BasketDeletetRequestSerializer, BuyerOrderPostRequestSerializer
from backend.signals import user_registered, new_orders_to_user, new_orders_to_admin
from backend.tasks import send_email_new_order_task, send_email_user_register_task, do_import_task
from django.contrib.auth.password_validation import validate_password


def is_owner(user_id, buyer_id):
    if Buyer.objects.filter(id=buyer_id, user_id=user_id).first():
        return True
    return False


@extend_schema(
    description=extend_schema_data['RegisterAccountView']['description'],
)
class RegisterAccountView(generics.CreateAPIView):
    """
    Регистрация нового пользователя. Обязательные поля - email и password.
    Переопределяются методы CreateModelMixin для дополнительной валидации, отправки JSON-ответов и email.
    В случае успеха пользователю по почте приходит токен для подтверждения аккаунта.
    """

    serializer_class = RegisterAccountSerializer

    def perform_create(self, serializer):
        password = serializer.validated_data['password']
        user = serializer.save()
        user.set_password(password)
        user.save()
        send_email_user_register_task(user.id)
        # user_registered.send(sender=self.__class__, instance=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            validate_password(serializer.validated_data['password'])
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response({'success': 'Пользователь зарегистрирован.'
                                    ' На Ваш email отправлен токен для подтверждения учетной записи'},
                        status=status.HTTP_201_CREATED)


class ConfirmAccountView(views.APIView):
    """Подтверждение аккаунта. Обязательные поля - email и token."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=extend_schema_data['ConfirmAccountView']['request'],
        responses=extend_schema_data['ConfirmAccountView']['responses'],

    )
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        token = request.data.get('token')
        if not all([email, token]):
            return Response({'error': 'Необходимые поля: email и token'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': f'Пользователя с email {email} не существует'}, status=status.HTTP_404_NOT_FOUND)
        try:
            confirm_token = ConfirmEmailToken.objects.get(user=user, email_token=token)
        except ConfirmEmailToken.DoesNotExist:
            return Response({'error': 'Токен не соответствует email'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save()
        confirm_token.delete()
        return Response({'success': 'Аккаунт успешно подтвержден'}, status=status.HTTP_200_OK)


class LoginView(views.APIView):
    """
    Вход в аккаунт. Обязательные поля - email и password
    В случае успеха в ответе приходит токен для использования в последующих запросах.
    """
    authentication_classes = [BasicAuthentication]

    @extend_schema(
        request=extend_schema_data['LoginView']['request'],
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', None)
        password = request.data.get('password', None)
        if not all([email, password]):
            return Response({'error': 'Необходимые поля: email и password'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': f'Пользователя с email {email} не существует'}, status=status.HTTP_404_NOT_FOUND)
        if not user.is_active:
            return Response({'error': 'Аккаунт был удален'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(email=email, password=password)
        if user is None:
            return Response({'error': 'Неверный пароль'},
                            status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'success': 'Успешный вход. Используйте токен в дальнейших запросах',
                         'token': token.key}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateDestroyAPIView):
    """Просмотр, обновление, удаление профиля пользователя"""

    permission_classes = [IsOwner, IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get(self, request, *args, **kwargs):
        """Просмотр профиля"""

        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Обновление профиля"""

        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        msg_email = ''
        if 'email' in request.data:
            user.email = request.data['email']
            user.email_confirmed = False
            user.save()
            Token.objects.filter(user=user).delete()
            send_email_user_register_task(user.id)
            # user_registered.send(sender=self.__class__, instance=user)
            msg_email = f'. На Ваш новый email отправлен токен для подтверждения аккаунта. ' \
                        f'Отправьте его на ...user/register/confirm/'

        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        self.perform_update(serializer)

        return Response({'status': f'Данные обновлены{msg_email}', 'data': serializer.data},
                        status=status.HTTP_200_OK)

    @extend_schema(
        responses=extend_schema_data['UserProfileView_DELETE']['responses'],
        description=extend_schema_data['UserProfileView_DELETE']['description'],)
    def delete(self, request, *args, **kwargs):
        """Удаление профиля. Не физическое удаление, а is_active=False, что для пользователя равносильно удалению"""

        user = request.user
        user.is_active = False
        user.save()
        Token.objects.filter(user=user).delete()
        return Response({'success': 'Аккаунт удален'}, status=status.HTTP_200_OK)


class BuyerViewSet(viewsets.ModelViewSet):
    """Просмотр, создание, изменение, удаление покупателей"""

    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer
    permission_classes = [BuyerViewPermission]

    def get_queryset(self):
        if self.action == 'list':
            if self.request.user.is_superuser:
                return Buyer.objects.all()
            return self.request.user.buyers.all()
        return Buyer.objects.all()

    def perform_create(self, serializer):
        # Устанавливаем поле 'user' на основании аутентификации (чтобы не отправлять его в запросе)
        serializer.save(user=self.request.user)


class SupplierViewSet(viewsets.ModelViewSet):
    """Просмотр, создание, изменение, удаление поставщиков"""

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [SupplierViewPermission]

    def perform_create(self, serializer):
        # Устанавливаем поле 'user' на основании аутентификации (чтобы не отправлять его в запросе)
        serializer.save(user=self.request.user)


class ProductCategoryView(generics.ListAPIView):
    """Просмотр категорий товаров"""

    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.all()



class PriceListUpdateView(views.APIView):
    """
    Обновление из файла. Пользователь отправляет post-запрос.
    Обязательные поля: supplier_id и file_url
    """

    permission_classes = [IsAuthenticated, IsSupplier]
    throttle_scope = 'price_list_update'

    @extend_schema(
        request=extend_schema_data['PriceListUpdateView']['request'],
    )
    def post(self, request):
        serializer = PriceListUpdateSerializer(data=request.data)
        if serializer.is_valid():
            file_url = serializer.validated_data['file_url']
            supplier_id = serializer.validated_data['supplier_id']
            user_id = request.user.id

            try:
                supplier = Supplier.objects.get(id=supplier_id, user_id=user_id)
            except Supplier.DoesNotExist:
                return Response({'error': f'У пользователя нет поставщика с id={supplier_id}'},
                                status=status.HTTP_400_BAD_REQUEST)

            if not file_url.endswith('.yaml'):
                return Response({'error': 'Неправильный формат файла, должен быть YAML.'},
                                status=status.HTTP_400_BAD_REQUEST)

            try:
                response = requests.get(file_url)
                response.raise_for_status()
                # y_data = yaml.load(response.content, Loader=SafeLoader)
                y_data = yaml.safe_load(response.content)
            except (requests.exceptions.RequestException, yaml.YAMLError) as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
                # return Response({'error': 'Некорректный  YAML-файл'}, status=status.HTTP_400_BAD_REQUEST)

            do_import_task(supplier_id, file_url, y_data)

            return Response({'success': True}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductSupplierView(views.APIView):
    """
    Просмотр товаров доступных поставщиков c возможностью выбора (через параметры запроса)
    по отдельным категориям, поставщикам, продуктам ('category_id, 'supplier_id, product_id)
    """

    @extend_schema(
        responses=extend_schema_data['ProductSupplierView']['responses'],
        parameters=extend_schema_data['ProductSupplierView']['parameters'],
    )
    def get(self, request, *args, **kwargs):

        # Если в запросе есть параметры supplier_id или category_id или product_id
        supplier_id = request.query_params.get('supplier_id')
        category_id = request.query_params.get('category_id')
        product_id = request.query_params.get('product_id')

        query = Q(supplier__is_available=True)
        if supplier_id:
            query &= Q(supplier_id=supplier_id)
        if category_id:
            query &= Q(product__category_id=category_id)
        if product_id:
            query &= Q(product_id=product_id)
        # Queryset c оптимизацией запросов к базе данных
        # select_related - когда выбираем один объект, prefetch_related - при выдаче нескольких объектов)
        queryset = ProductSupplier.objects.filter(
            query
        ).select_related(
            'supplier', 'product__category'
        ).prefetch_related(
            'p_parameters__parameter'
        ).distinct()

        serializer = ProductSupplierSerializer(queryset, many=True)
        return Response(serializer.data)


class BasketView(views.APIView):
    """Корзины покупателей: просмотр, создание/изменение, удаление"""

    permission_classes = [IsAuthenticated, IsBuyer]

    def setup(self, request, *args, **kwargs):
        """Initialize attributes shared by all view methods."""
        super().setup(request, *args, **kwargs)
        self.product_supplier_map = {}
        for ps in ProductSupplier.objects.filter(supplier__is_available=True):
            self.product_supplier_map[(ps.product_id, ps.supplier_id)] = ps

    def _is_valid_values(self, items):
        """
        Проверка значений в запросе для полей, входящих в items
        """
        for item in items:
            quantity = item['quantity']
            product_supplier = self._get_product_supplier(item)
            if not product_supplier or quantity > product_supplier.quantity:
                return False
        return True

    def _get_product_supplier(self, item):
        product_id = item['product_id']
        supplier_id = item['supplier_id']
        return self.product_supplier_map.get((product_id, supplier_id))

    @extend_schema(
                    request=extend_schema_data['BasketView_POST']['request'],
                    responses=extend_schema_data['BasketView_POST']['responses'],
                    description=extend_schema_data['BasketView_POST']['description']
                   )
    def post(self, request):
        """
        Создание заказа (статус 'basket') и позиций заказа.
        Если заказ уже создан, то создаются только позиции заказа.
        Если позиции уже есть, то они могут изменяться (только 'quantity')
        Формат запроса:
            [{"buyer_id": int, "items": [{"product_id": int, "supplier_id": int, "quantity": int },
                                        {"product_id": int, "supplier_id": int, "quantity": int}
                                        ]},
             {"buyer_id": int, "items": [{"product_id": int, "supplier_id": int, "quantity": int},
                                        {"product_id": int, "supplier_id": int, "quantity": int}
                                        ]}
            ]
        """
        serializer = BasketPostRequestSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data

        added = {}
        for buyer_data in request_data:
            buyer_id = buyer_data['buyer_id']
            items = buyer_data.get("items")
            if not is_owner(self.request.user.id, buyer_id):
                return Response({'error': f'Некорректный {buyer_id=}'}, status=status.HTTP_400_BAD_REQUEST)
            if not self._is_valid_values(items):
                return Response({'error': f'Некорректные значения в items для {buyer_id=}'}, status=status.HTTP_400_BAD_REQUEST)
            order, _ = Order.objects.get_or_create(buyer_id=buyer_id, state='basket')
            objects_added = 0
            for item in items:
                quantity = item['quantity']
                product_supplier = self._get_product_supplier(item)
                data = {'order': order.id, 'product_supplier': product_supplier.id, 'quantity': quantity}
                serializer = OrderItemSerializer(data=data)
                if serializer.is_valid():
                    try:
                        serializer.save()
                    except IntegrityError as e:
                        return Response({'error': str(e)})
                    else:
                        objects_added += 1
                else:
                    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            added[order.id] = objects_added

        return Response({'success': f'{added}'}, status=status.HTTP_201_CREATED)

    @extend_schema(exclude=True)
    def put(self, request):

        return Response({'error': 'PUT метод не разрешен. Используйте POST и DELETE методы'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(responses=extend_schema_data['BasketView_DELETE']['responses'],
                   description=extend_schema_data['BasketView_DELETE']['description']
                   )
    def delete(self, request):
        """
        Удаление позиций из заказа покупателей по номеру позиции в заказе
        Примерный формат: [{"buyer_id": <id>, "items": [<order_item_id>>, <order_item_id>]},
                            {"buyer_id": <id>> "items": [<order_item_id>>]}
                            ]
        """
        serializer = BasketDeletetRequestSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data

        response_data = {}
        for buyer_data in request_data:
            buyer_id = buyer_data['buyer_id']
            items = buyer_data.get("items")

            if not is_owner(self.request.user.id, buyer_id):
                response_data[buyer_id] = {'error': f'Некорректный {buyer_id=}'}
                continue

            order = Order.objects.filter(buyer_id=buyer_id, state='basket').first()

            if not order:
                response_data[buyer_id] = {'error': f'Не найдено корзины для покупателя с id={buyer_id}'}
                continue
            query = Q()
            objects_deleted = 0
            for item in items:
                query = query | Q(order_id=order.id, id=item)
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                objects_deleted += deleted_count

            if objects_deleted:
                response_data[buyer_id] = {'success': f'Удалено позиций: {objects_deleted} (заказ №{order.id})'}
            else:
                response_data[buyer_id] = {'error': f'Нет таких позиций {items} в корзине (заказ №{order.id})'}

        if all('error' in value for value in response_data.values()):
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        elif all('success' in value for value in response_data.values()):
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_206_PARTIAL_CONTENT)

    @extend_schema(responses=extend_schema_data['BasketView']['responses'])
    def get(self, request):
        """Просмотр корзины каждого покупателя, созданного пользователем"""

        user = request.user
        buyers = user.buyers.all()
        orders = Order.objects.filter(buyer__in=buyers, state='basket').select_related('buyer')

        data = []
        # Цикл по корзинам (по сути по покупателям, т.к. у одного покупателя только одна корзина)
        for order in orders:
            order_items = OrderItem.objects.filter(order=order).select_related('product_supplier')

            order_items_data = []
            order_sum = 0

            # Цикл по позициям корзины покупателя
            for order_item in order_items:
                product_supplier = order_item.product_supplier
                item_sum = product_supplier.price * order_item.quantity
                order_item_data = {
                    'id': order_item.id,
                    'product_supplier_id': product_supplier.id,
                    'product_name': product_supplier.product.name,
                    'quantity': order_item.quantity,
                    'sum': item_sum
                }
                # добавляем данные по отдельной позиции корзины
                order_items_data.append(order_item_data)
                order_sum += item_sum

            # добавляем блок данных по корзине покупателя
            data.append({
                'buyer_id': order.buyer.id,
                'order_id': order.id,
                'order_sum': order_sum,
                'order_items': order_items_data,
            })
        serializer = BasketGetSerializer(data, many=True)
        return Response(serializer.data)


class BuyerOrderView(views.APIView):
    """
    Получение и размещение заказов покупателей пользователем
    """

    permission_classes = [IsAuthenticated, IsBuyer]

    @extend_schema(responses=extend_schema_data['BuyerOrderView']['responses'])
    def get(self, request):
        """Просмотр заказов покупателей"""

        user = request.user
        buyers = user.buyers.all()

        buyer_data = []
        # Цикл по покупателям, созданных пользователем
        for buyer in buyers:
            orders = Order.objects.filter(buyer=buyer).exclude(state='basket')

            orders_data = []
            buyer_sum = 0
            # Цикл по заказам покупателя
            for order in orders:
                order_items = OrderItem.objects.filter(order=order)

                order_items_data = []
                order_sum = 0
                # Цикл по позициям заказа
                for order_item in order_items:
                    product_supplier = order_item.product_supplier
                    item_sum = product_supplier.price * order_item.quantity
                    order_item_data = {
                        'id': order_item.id,
                        'product_supplier_id': product_supplier.id,
                        'product_name': product_supplier.product.name,
                        'quantity': order_item.quantity,
                        'sum': item_sum
                    }
                    # добавляем данные по отдельной позиции заказа
                    order_items_data.append(order_item_data)
                    order_sum += item_sum

                # добавляем блок данных по заказу
                orders_data.append({
                    'id': order.id,
                    'state': order.state,
                    'order_sum': order_sum,
                    'order_items': order_items_data,
                })
                buyer_sum += order_sum

            # добавляем блок данных по покупателю
            buyer_data.append({
                'buyer_id': buyer.id,
                'buyer_sum': buyer_sum,
                'orders': orders_data,
            })
        serializer = BuyerOrderGetSerializer(buyer_data, many=True)
        return Response(serializer.data)

    @extend_schema(
                    request=extend_schema_data['BuyerOrderView_POST']['request'],
                    # responses={201: 'success'},
                    responses=extend_schema_data['BuyerOrderView_POST']['responses'],
    )
    def post(self, request):
        """
        Размещение заказов (изменение статуса с 'basket' на 'new').
        Формат запроса: {'orders_ids':[int, int...]}
        """
        user = request.user

        serializer = BuyerOrderPostRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_data = serializer.validated_data

        r_orders_ids = set(request_data['orders_ids'])

        # заказы со статусом 'basket' покупателей, принадлежащих пользователю
        orders = Order.objects.filter(buyer__in=request.user.buyers.all(), state='basket')

        # id заказов со статусом 'basket' покупателей, принадлежащих пользователю
        orders_ids = set([order.id for order in orders])

        # к размещению (пересечение данных запроса с тем, что есть в БД)
        to_place_orders_ids = r_orders_ids & orders_ids

        # лишнее в запросе (не найдено соответствия в БД: либо не 'basket, 'либо не владелец, либо нет id)
        wrong_orders_ids = r_orders_ids - to_place_orders_ids

        if not to_place_orders_ids:
            return Response({'error': f'Некорректные значения id: {r_orders_ids}'}, status=status.HTTP_400_BAD_REQUEST)
        placed_orders = Order.objects.filter(id__in=to_place_orders_ids)
        updated = placed_orders.update(state='new')
        # updated = Order.objects.filter(id__in=to_place_orders_ids).update(state='new')

        if updated:
            admin_emails = [admin.email for admin in CustomUser.objects.filter(is_superuser=True, is_active=True)]
            for order_id in to_place_orders_ids:
                send_email_new_order_task.delay(order_id=order_id, user_email=user.email, admin_emails=admin_emails)
                # new_orders_to_user.send(sender=self.__class__, user=user, orders=placed_orders)

            if not wrong_orders_ids:
                return Response({'success': f'Успешное размещение: {to_place_orders_ids}'},
                                status=status.HTTP_201_CREATED)
            return Response({'partial success': f'Успешное размещение: {to_place_orders_ids}. '
                                                f'Некорректные значения: {wrong_orders_ids}'},
                            status=status.HTTP_206_PARTIAL_CONTENT)
        return Response({'error': f'Проблемы с обновлением'}, status=status.HTTP_404_NOT_FOUND)


class SupplierOrderGetView(views.APIView):
    """
    Получения поставщиками информации о заказанных позициях (по товарам из их прайса)
    """

    permission_classes = [IsAuthenticated, IsSupplier]

    @extend_schema(responses=extend_schema_data['SupplierOrderGetView']['responses'])
    def get(self, request):
        """Просмотр заказов покупателей"""

        user = request.user
        suppliers = user.suppliers.all()

        supplier_data = []
        # Цикл по поставщикам пользователя
        for supplier in suppliers:
            orders = Order.objects.filter(
                order_items__product_supplier__supplier=supplier).exclude(
                state='basket').distinct()

            orders_data = []
            supplier_sum = 0
            # Цикл по заказам покупателя
            for order in orders:
                order_items = OrderItem.objects.filter(order=order)

                order_items_data = []
                order_sum = 0
                # Цикл по позициям заказа
                for order_item in order_items:
                    product_supplier = order_item.product_supplier

                    if product_supplier.supplier.id != supplier.id:
                        continue
                    item_sum = product_supplier.price * order_item.quantity
                    order_item_data = {
                        'product_supplier_id': product_supplier.id,
                        'product_name': product_supplier.product.name,
                        'external_id': product_supplier.external_id,
                        'quantity': order_item.quantity,
                        'sum': item_sum
                    }
                    # добавляем данные по отдельной позиции заказа
                    order_items_data.append(order_item_data)
                    order_sum += item_sum

                # добавляем блок данных по заказу
                orders_data.append({
                    'id': order.id,
                    'buyer_id': order.buyer.id,
                    'state': order.state,
                    'order_sum': order_sum,
                    'order_items': order_items_data,
                })
                supplier_sum += order_sum

            # добавляем блок данных по покупателю
            supplier_data.append({
                'supplier_id': supplier.id,
                'supplier_sum': supplier_sum,
                'orders': orders_data,
            })
        serializer = SupplierOrdertGetSerializer(supplier_data, many=True)
        return Response(serializer.data)


class CustomConvertTokenView(ConvertTokenView):

    @extend_schema(
        request=extend_schema_data['ConvertTokenView']['request'],
        responses=extend_schema_data['ConvertTokenView']['responses'],
        description=extend_schema_data['ConvertTokenView']['description'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

