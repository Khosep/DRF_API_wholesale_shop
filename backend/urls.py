from django.urls import path
from backend.views import *
from rest_framework import routers
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

router = routers.DefaultRouter()
router.register('buyer', BuyerViewSet)
router.register('supplier', SupplierViewSet)

app_name = 'backend'

urlpatterns = [
    path('user/register/', RegisterAccountView.as_view(), name='user-register'),
    path('user/register/confirm/', ConfirmAccountView.as_view(), name='user-register-confirm'),
    path('user/login/', LoginView.as_view(), name='user-login'),
    path('user/password_reset/', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm/', reset_password_confirm, name='password_reset-confirm'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('category/', ProductCategoryView.as_view(), name='category'),
    path('supplier/price-list/', PriceListUpdateView.as_view(), name='supplier-price-list'),
    path('supplier/products/', ProductSupplierView.as_view(), name='supplier-products'),
    path('buyer/basket/', BasketView.as_view(), name='buyer-basket'),
    path('buyer/order/', BuyerOrderView.as_view(), name='buyer-order'),
    path('supplier/order/', SupplierOrderGetView.as_view(), name='supplier-order'),
]
urlpatterns += router.urls
