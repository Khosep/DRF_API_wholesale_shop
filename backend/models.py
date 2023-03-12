from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import validate_email
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator

USER_TYPE_CHOICES = (
    ('supplier', 'Поставщик'),
    ('buyer', 'Покупатель'),
)

STATE_CHOICES = (
    ('basket', 'В корзине'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)


class CustomUserManager(BaseUserManager):
    """Пользовательский UserManager, где email является уникальным идентификатором для аутентификации вместо username"""

    # If set to True the manager will be serialized into migrations and will thus be available in e.g. RunPython operations.
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Создает и сохраняет пользователя с указанным email и password."""
        if not email:
            raise ValueError('The email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        user.set_password(password)
        # user.make_password(password)

        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Создает пользователя с указанным email и password"""

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Создает суперпользователя с указанным email и password"""

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_active') is not True:
            raise ValueError('Superuser must have is_active=True.')
        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Пользователь (поставщик или покупатель). На базе стандартной модели. Поле email - уникально, username отсутствует
    """

    objects = CustomUserManager()

    #  имя поля, используемое в качестве уникального идентификатора.
    USERNAME_FIELD = 'email'

    # Список имен полей, которые будут запрашиваться при создании пользователя командой createsuperuser
    REQUIRED_FIELDS = []

    email = models.EmailField(_('email address'),
                              unique=True,
                              validators=[validate_email],
                              error_messages={
                                  "unique": _("Email already registered.")
                              }
                              )

    company = models.CharField(max_length=45, blank=True, verbose_name='Компания')
    position = models.CharField(max_length=45, blank=True, verbose_name='Должность')

    # Убираем
    username = None

    is_active = models.BooleanField(default=False, verbose_name='Активен')
    type = models.CharField(choices=USER_TYPE_CHOICES, max_length=10, default='buyer', verbose_name='Тип пользователя')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Пользователи"
        ordering = ('type', 'email',)

    def __str__(self):
        return f'{self.pk}. {self.email} - {self.first_name} {self.last_name}'


class ConfirmEmailToken(models.Model):
    """Подтверждение email"""
    user = models.ForeignKey(CustomUser, related_name='confirm_email_tokens', on_delete=models.CASCADE,
                             verbose_name='Пользователь')
    email_token = models.CharField(max_length=64, unique=True, db_index=True, verbose_name='Токен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Сгенерирован')


    class Meta:
        verbose_name = 'Токен подтверждения email'
        verbose_name_plural = 'Токены подтверждения email'

    @staticmethod
    def generate_email_token():
        """ Генерация email_token"""
        return get_token_generator().generate_token()


    def save(self, *args, **kwargs):
        if not self.email_token:
            self.email_token = self.generate_email_token()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return f'Токен для {self.user}'


class Supplier(models.Model):
    """ Поставщик продукции для магазина"""

    user = models.ForeignKey(CustomUser, related_name='suppliers', on_delete=models.CASCADE, verbose_name='Владелец')

    name = models.CharField(max_length=70, verbose_name='Название')
    person = models.CharField(max_length=70, verbose_name='Контактное лицо')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    file_url = models.URLField(null=True, blank=True, verbose_name='Ссылка на файл')

    # Поставщик может включать и отключать доступность своих товаров для заказа
    is_available = models.BooleanField(default=True, verbose_name='Доступность для заказа')

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = "Список поставщиков"
        ordering = ('-is_available', 'id',)

    def __str__(self):
        return f'{self.pk}.{self.name}-{self.is_available}-u:{self.user.id}'


class ProductCategory(models.Model):
    """Категория продукта"""

    name = models.CharField(max_length=60, verbose_name='Категория')
    suppliers = models.ManyToManyField(Supplier, blank=True, related_name='categories', verbose_name='Поставщики')

    class Meta:
        verbose_name = 'Категория продукта'
        verbose_name_plural = "Список категорий"
        ordering = ('name',)

    def __str__(self):
        return f'{self.pk}.{self.name}'


class Product(models.Model):
    """Продукт"""

    name = models.CharField(max_length=150, unique=True, verbose_name='Название')
    category = models.ForeignKey(ProductCategory, related_name='products', on_delete=models.CASCADE,
                                 verbose_name='Категория')

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = "Список продуктов"
        ordering = ('name',)

    def __str__(self):
        return f'{self.pk}.{self.name}'


class ProductSupplier(models.Model):
    """Продукт от поставщика"""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, related_name='s_products',
                                verbose_name='Продукт')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, blank=True, related_name='s_products',
                                 verbose_name='Поставщик')
    external_id = models.PositiveIntegerField(verbose_name='Внешний ID')
    model = models.CharField(max_length=100, verbose_name="Модель")
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')
    price_rrc = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Розничная цена')
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Информация о продукте поставщика'
        verbose_name_plural = 'Информация о продуктах поставщика'
        constraints = [models.UniqueConstraint(fields=['product', 'supplier'], name='unique_product_supplier')]

    def __str__(self):
        return f'{self.pk}.p:{self.product_id}-s:{self.supplier_id}'


class Parameter(models.Model):
    """Параметр"""

    name = models.CharField(max_length=50, unique=True, verbose_name='Название')

    class Meta:
        verbose_name = 'Название параметра'
        verbose_name_plural = "Список названий параметров"
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}'


class ProductSupplierParameter(models.Model):
    """Параметр и его значение, связанные с поставщиком"""

    product_supplier = models.ForeignKey(ProductSupplier, blank=True, on_delete=models.CASCADE,
                                         related_name='p_parameters', verbose_name='Продукт')
    parameter = models.ForeignKey(Parameter, blank=True, on_delete=models.CASCADE, related_name='p_parameters',
                                  verbose_name='Параметр')
    value = models.CharField(max_length=120, verbose_name='Значение')

    class Meta:
        verbose_name = 'Параметр продукта поставщика'
        verbose_name_plural = 'Список параметров'
        constraints = [
            models.UniqueConstraint(fields=['product_supplier', 'parameter'], name='unique_product_parameter')]

    def __str__(self):
        return f'{self.pk} {self.parameter.name}'


class Buyer(models.Model):
    """Контактные данные покупателя"""

    user = models.ForeignKey(CustomUser, related_name='buyers', on_delete=models.CASCADE, verbose_name='Владелец')
    name = models.CharField(max_length=70, verbose_name='Название')
    person = models.CharField(max_length=70, verbose_name='Контактное лицо')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    region = models.CharField(max_length=30, blank=True, verbose_name='Регион')
    district = models.CharField(max_length=30, blank=True, verbose_name='Район')
    locality_name = models.CharField(max_length=50, verbose_name='Название населенного пункта')
    street = models.CharField(max_length=80, blank=True, verbose_name='Улица')
    house = models.CharField(max_length=15, blank=True, verbose_name='Дом')
    structure = models.CharField(max_length=15, blank=True, verbose_name='Корпус')
    building = models.CharField(max_length=15, blank=True, verbose_name='Строение')
    apartment = models.CharField(max_length=15, blank=True, verbose_name='Квартира')

    class Meta:
        verbose_name = 'Покупатель'
        verbose_name_plural = "Список покупателей"
        ordering = ('id',)

    def __str__(self):
        return f'{self.pk}. {self.name}'


class Order(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name='orders', verbose_name='Покупатель')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Изменен')
    state = models.CharField(max_length=15, choices=STATE_CHOICES, default='basket', verbose_name='Статус')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = "Список заказов"
        ordering = ('created_at',)

    def __str__(self):
        return f'{self.pk}. {self.buyer_id} - {self.state}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', blank=True,
                              on_delete=models.CASCADE, verbose_name='Заказ')

    product_supplier = models.ForeignKey(ProductSupplier, related_name='order_items', blank=True,
                                     on_delete=models.CASCADE, verbose_name='Информация о продукте')
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = "Список заказанных позиций"
        constraints = [
            models.UniqueConstraint(fields=['order', 'product_supplier'],
                                    condition=models.Q(quantity__gt=0),
                                    name='unique_order_item'),
        ]

    def __str__(self):
        return f'{self.pk}. {self.quantity}'
