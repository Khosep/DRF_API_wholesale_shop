from django.urls import path
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from backend.serializers import SupplierOrdertGetSerializer, BasketGetSerializer, \
    BuyerOrderGetSerializer, BuyerOrderPostRequestSerializer, \
    BasketPostRequestSerializer, PriceListUpdateSerializer, ProductSupplierSerializer

schema_urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

extend_schema_data = {
    'BasketView': {'responses': BasketGetSerializer},
    'BasketView_POST': {
                        'request': BasketPostRequestSerializer(many=True),
                        'description': "Создание заказа (статус 'basket') и позиций заказа. "
                                       "Если заказ уже создан, то создаются только позиции заказа. "
                                       "Если позиции уже есть, то они могут изменяться (только 'quantity')",
                        'responses':    {
                            201: {
                                'type': 'object',
                                'properties': {'success': {'type': 'object', 'additionalProperties': {'type': 'integer'}}},
                                'example': {
                                    'success': {
                                        22: 3,
                                        24: 1,
                                        38: 5
                                    }
                                }
                                },

                            'default': {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
                                        }
                        },
    'BasketView_DELETE': {
                        'description': 'Удаление позиций из заказа покупателей по номеру позиции в заказе. '
                                       'Формат запроса:\n\n'
                                       '    [{"buyer_id": <id>, "items": [<order_item_id>>, ...]},\n\n'
                                       '     {"buyer_id": <id>> "items": [<order_item_id>>, ...]},\n\n'
                                   '         ...\n\n'
                                       '    ]',

                        'responses': {
                            200: {
                                'type': 'object',
                                'properties': {
                                    'success': {
                                        'type': 'object',
                                        'additionalProperties': {'type': 'string'},
                                        'example': {
                                            2: 'Удалено позиций: 5 (заказ №22)',
                                            5: 'Удалено позиций: 2 (заказ №23)'
                                                    }
                                                }
                                                },
                                },
                            400: {
                                'type': 'object',
                                'properties': {
                                    'error': {
                                        'type': 'object',
                                        'additionalProperties': {'type': 'string'},
                                        'example': {
                                            2: 'Нет таких позиций [84, 94] в корзине (заказ №22)',
                                            5: 'Нет таких позиций [88, 141] в корзине (заказ №23)',
                                                    }
                                                }
                                                },
                                },
                                    },
                        },

    'BuyerOrderView': {'responses': BuyerOrderGetSerializer(many=True)},
    'BuyerOrderView_POST': {
                        'request': BuyerOrderPostRequestSerializer,
                        'responses':    {
                            201:    {
                                'type': 'object',
                                'properties': {
                                    'success': {
                                        'type': 'string',
                                        'example': 'Успешное размещение: {22, 23}',
                                                }
                                                }
                                    },
                                        },
                            },

    'SupplierOrderGetView': {'responses': SupplierOrdertGetSerializer},

    'PriceListUpdateView': {
        'request': PriceListUpdateSerializer,
                            },

    'ProductSupplierView': {
        'responses': ProductSupplierSerializer(many=True),
        'parameters': [
            OpenApiParameter(
                name='supplier_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by supplier ID'
            ),
            OpenApiParameter(
                name='category_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by category ID'
            ),
            OpenApiParameter(
                name='product_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by product ID'
            ),
        ],
    },

    'LoginView': {
        'request': {
            'schema': {
                    'type': 'object',
                    'properties': {
                        'email': {'type': 'string'},
                        'password': {'type': 'string'},
                    },
                    'required': ['email', 'password']
                        },
            'application/json': {
                    'example': {'email': 'user@example.com',
                                'password': '123qwerty',
                                }
                                 },
                    },
    },

    'UserProfileView_DELETE': {
                        'responses':    {
                            200:    {
                                'type': 'object',
                                'properties': {
                                    'success': {
                                        'type': 'string',
                                        'example': 'Аккаунт удален',
                                                }
                                                }
                                    },
                                        },
                        'description': 'Удаление профиля',
                            },

    'RegisterAccountView': {
                        'description': 'Регистрация нового пользователя. Обязательные поля - email и password. '
                                       'В случае успеха пользователю по почте приходит токен для подтверждения аккаунта.',
                            },

    'ConfirmAccountView': {
        'request': {
            'schema': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string'},
                    'token': {'type': 'string'},
                },
                'required': ['email', 'password']
            },
            'application/json': {
                'example': {'email': 'user@example.com',
                            'token': 'er12zsg7flGl124sdf45',
                            }
            },
                    },
        'responses': {
            200: {
                'type': 'object',
                'properties': {
                    'success': {
                        'type': 'string',
                        'example': 'Аккаунт успешно подтвержден',
                    }
                                }
                },
                    },

                            },


    'ConvertTokenView': {
        'request': {
            'schema': {
                'type': 'object',
                'properties': {
                    'grant_type': {'type': 'string', 'example': 'convert_token'},
                    'client_id': {'type': 'string', 'example': 'id_app_created_in_Django_Oauth_toolkit'},
                    'backend': {'type': 'string', 'example': 'yandex-oauth2'},
                    'token': {'type': 'string', 'example': 'your_yandex_token'},
                },
                'required': ['grant_type', 'client_id', 'backend', 'token']
            },
        },
        'responses': {
            200: {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string'},
                    'expires_in': {'type': 'number'},
                    'scope': {'type': 'string'},
                    'refresh_token': {'type': 'string'},
                    'token_type': {'type': 'string'},
                                },
                     },
        },
        'description': 'Обмен токена социальной сети на токен аутентификации',
    },
}
