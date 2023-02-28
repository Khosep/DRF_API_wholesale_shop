import pytest
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_201_CREATED, \
    HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, HTTP_204_NO_CONTENT
from rest_framework.authtoken.models import Token
from django.core import mail
from backend.models import ConfirmEmailToken, CustomUserManager, Buyer, CustomUser, Supplier, Order

@pytest.mark.django_db
def test_register_201(client, django_user_model):
    url = reverse('backend:user-register')
    data = {'email': 'test-2@test.te', 'password': '2-12345Qwer', 'type': 'supplier'}
    response = client.post(url, data)
    new_user = django_user_model.objects.get(email=data['email'])

    assert response.status_code == HTTP_201_CREATED
    assert response.json()['success'][:29] == 'Пользователь зарегистрирован.'
    assert new_user.is_active is False
    assert new_user.is_superuser is False
    assert new_user.type == 'supplier'

@pytest.mark.django_db
def test_register_400_invalid_password(client, django_user_model):
    url = reverse('backend:user-register')
    data = {'email': 'test-3@test.te', 'password': 'password'}
    response = client.post(url, data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert 'error' in response.json()

@pytest.mark.django_db
def test_register_400_invalid_field(client, user, django_user_model):
    url = reverse('backend:user-register')
    data = {'email': 'test-4@test.te', 'password': '4-12345Qwer', 'company': 'a'*50}
    response = client.post(url, data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert 'company' in response.json()

#___________________________________________________________________________________________________________


@pytest.mark.django_db
def test_confirm_account_200(client, inactive_user, django_user_model):
    token, _ = ConfirmEmailToken.objects.get_or_create(user=inactive_user)
    email_token = token.email_token
    url = reverse('backend:user-register-confirm')
    data = {'email': 'test-ina@test.te', 'token': email_token}
    response = client.post(url, data)
    inactive_user = CustomUser.objects.get(email='test-ina@test.te')

    assert response.status_code == HTTP_200_OK
    assert response.json()['success'] == 'Аккаунт успешно подтвержден'
    assert inactive_user.is_active

@pytest.mark.django_db
def test_confirm_account_404_user_not_found(client, inactive_user, django_user_model):
    token, _ = ConfirmEmailToken.objects.get_or_create(user=inactive_user)
    email_token = token.email_token
    wrong_email = 'wrong_email@wrong.org'
    url = reverse('backend:user-register-confirm')
    data = {'email': wrong_email, 'token': email_token}
    response = client.post(url, data)

    assert response.status_code == HTTP_404_NOT_FOUND
    assert 'error' in response.json()
    assert response.json()['error'] == f'Пользователя с email {wrong_email} не существует'

@pytest.mark.django_db
def test_confirm_account_400_wrong_token(client, inactive_user, django_user_model):
    ConfirmEmailToken.objects.get_or_create(user=inactive_user)
    wrong_token = 'wrong_token'
    url = reverse('backend:user-register-confirm')
    data = {'email': 'test-ina@test.te', 'token': wrong_token}
    response = client.post(url, data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert 'error' in response.json()
    assert response.json()['error'] == 'Токен не соответствует email'

@pytest.mark.django_db
def test_confirm_account_400_without_required_field(client, inactive_user, django_user_model):
    ConfirmEmailToken.objects.get_or_create(user=inactive_user)
    url = reverse('backend:user-register-confirm')
    data = {'email': 'test-ina@test.te'}
    response = client.post(url, data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert 'error' in response.json()
    assert response.json()['error'] == 'Необходимые поля: email и token'
#___________________________________________________________________________________________________________


@pytest.mark.django_db
def test_login_200(client, user):
    url = reverse('backend:user-login')
    data = {'email': user.email, 'password': '1-12345Qwer'}
    response = client.post(url, data)
    token = Token.objects.get(user=user)

    assert response.status_code == HTTP_200_OK
    assert response.json()['token'] == token.key
    assert 'error' not in response.json()

@pytest.mark.django_db
def test_login_400(client, user):
    url = reverse('backend:user-login')
    data = {'email': user.email}
    response = client.post(url, data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()['error'] == 'Необходимые поля: email и password'
    assert 'token' not in response.json()

@pytest.mark.django_db
def test_login_401_inactive_account(client, inactive_user):
    url = reverse('backend:user-login')
    data = {'email': inactive_user.email, 'password': 'wrong_password'}
    response = client.post(url, data)

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json()['error'] == 'Аккаунт был удален'
    assert 'error' in response.json()
    assert 'token' not in response.json()

@pytest.mark.django_db
def test_login_401_wrong_password(client, user):
    url = reverse('backend:user-login')
    data = {'email': user.email, 'password': 'wrong_password'}
    response = client.post(url, data)

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.json()['error'] == 'Неверный пароль'
    assert 'error' in response.json()
    assert 'token' not in response.json()

@pytest.mark.django_db
def test_login_404_user_not_found(client, user):
    url = reverse('backend:user-login')
    email = 'wrong_email'
    data = {'email': 'wrong_email', 'password': '1-12345Qwer'}
    response = client.post(url, data)

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()['error'] == f'Пользователя с email {email} не существует'
    assert 'error' in response.json()
    assert 'token' not in response.json()

#___________________________________________________________________________________________________________

@pytest.mark.django_db
def test_profile_get_200_buyers(client, user, user_2, get_token):
    token = get_token
    url = reverse('backend:user-profile')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    Buyer.objects.create(name='Test_Buyer', person='Тестова Таня', phone='+79252551', user_id=user_2.id)

    Buyer.objects.create(name='Test_Buyer2', person='Тестовая Таня', phone='+79252552', user_id=user.id)
    Buyer.objects.create(name='Test_Buyer3', person='Тестовчук Таня', phone='+79252553', user_id=user.id)

    response = client.get(url)
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json['email'] == user.email
    assert 'buyers' in response_json
    assert len(response_json['buyers']) == 2
    assert response_json['buyers'][0]['person'] == 'Тестовая Таня'
    assert response_json['buyers'][1]['name'] == 'Test_Buyer3'
    assert 'suppliers' not in response_json

@pytest.mark.django_db
def test_profile_get_200_suppliers(client, user, user_2, get_token):
    token = get_token
    url = reverse('backend:user-profile')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    user.type = 'supplier'
    user.save()
    user_2.type ='supplier'
    user_2.save()
    Supplier.objects.create(name='Test_Buyer', person='Тестова Таня', phone='+79252551', user_id=user_2.id)
    Supplier.objects.create(name='Test_Buyer2', person='Тестовая Таня', phone='+79252552', user_id=user.id)
    Supplier.objects.create(name='Test_Buyer3', person='Тестовчук Таня', phone='+79252553', user_id=user.id)
    response = client.get(url)
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json['email'] == user.email
    assert 'suppliers' in response_json
    assert len(response_json['suppliers']) == 2
    assert response_json['suppliers'][0]['person'] == 'Тестовая Таня'
    assert response_json['suppliers'][1]['name'] == 'Test_Buyer3'
    assert 'buyers' not in response_json

@pytest.mark.django_db
def test_profile_401(client, user):
    url = reverse('backend:user-profile')
    response = client.get(url)

    assert response.status_code == HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_profile_patch_200(client_with_credentials, user):
    url = reverse('backend:user-profile')
    user.company = 'Insignificance'
    user.save()
    data = {'company': 'Splendor', 'first_name': 'Frank', 'is_active': False, 'type': 'supplier'}
    response = client_with_credentials.patch(url, data)
    response_json = response.json()
    user_updated = CustomUser.objects.get(email='test@test.te')

    assert response.status_code == HTTP_200_OK
    assert response_json['status'] == 'Данные обновлены'
    assert user_updated.company == data['company']
    assert user_updated.first_name == data['first_name']
    assert user_updated.type == data['type']
    assert user_updated.is_active
    assert 'suppliers' in response_json['data']

@pytest.mark.django_db
def test_profile_put_200(client_with_credentials, user):
    url = reverse('backend:user-profile')
    user.position = 'manager'
    user.save()
    data = {'company': 'Splendor', 'first_name': 'Frank', 'is_active': False, 'type': 'supplier'}
    response = client_with_credentials.put(url, data)
    response_json = response.json()
    user_updated = CustomUser.objects.get(email='test@test.te')

    assert response.status_code == HTTP_200_OK
    assert response_json['status'] == 'Данные обновлены'
    assert user_updated.company == data['company']
    assert user_updated.first_name == data['first_name']
    assert user_updated.type == data['type']
    assert user_updated.position == 'manager'
    assert user_updated.is_active
    assert 'suppliers' in response_json['data']


@pytest.mark.django_db
def test_profile_delete_200(client, user, get_token):
    token = get_token
    url = reverse('backend:user-profile')
    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    response = client.delete(url)
    response_json = response.json()
    user_deleted = CustomUser.objects.get(email='test@test.te')
    token_deleted = Token.objects.filter(user=user_deleted).first()

    assert response.status_code == HTTP_200_OK
    assert response_json['success'] == 'Аккаунт удален'
    assert not token_deleted
    assert not user_deleted.is_active
#___________________________________________________________________________________________________________

@pytest.mark.django_db
def test_buyer_get_list_200(client_with_credentials, user, user_2, model_factory):
    url = reverse('backend:buyer-list')
    model_factory(Buyer, name='Покупатель 1', user=user)
    model_factory(Buyer, name='Покупатель 2', user=user)
    model_factory(Buyer, name='Покупатель 3', user=user_2)
    response = client_with_credentials.get(url)
    response_json = response.json()
    buyers_names = [b['name'] for b in response_json["results"]]

    assert response.status_code == HTTP_200_OK
    assert response_json['count'] == 2
    assert ('Покупатель 1' and 'Покупатель 2') in buyers_names
    assert 'Покупатель 3' not in buyers_names


@pytest.mark.django_db
def test_buyer_get_list_200_superuser(client_with_credentials, user, user_2, model_factory):
    url = reverse('backend:buyer-list')
    user.is_superuser = True
    user.save()
    model_factory(Buyer, name='Покупатель 1', user=user)
    model_factory(Buyer, name='Покупатель 2', user=user)
    model_factory(Buyer, name='Покупатель 3', user=user_2)
    response = client_with_credentials.get(url)
    response_json = response.json()
    buyers_names = [b['name'] for b in response_json["results"]]

    assert response.status_code == HTTP_200_OK
    assert response_json['count'] == 3
    assert ('Покупатель 1' and 'Покупатель 2' and 'Покупатель 3') in buyers_names

@pytest.mark.django_db
def test_buyer_get_list_403(client, user, get_token):
    url = reverse('backend:buyer-list')
    token = get_token
    user.type = 'supplier'
    user.save()
    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    response = client.get(url)
    response_json = response.json()

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response_json['detail'] == 'У вас недостаточно прав для выполнения данного действия.'


@pytest.mark.django_db
def test_buyer_get_retrieve_200(client_with_credentials, user, model_factory):
    pattern = 'Покупатель 2'
    buyers_names = ('Покупатель 1', 'Покупатель 2', 'Покупатель 3')
    buyers = [model_factory(Buyer, name=name, user=user) for name in buyers_names]
    buyer_id = next(b for b in buyers if b.name == pattern).id
    url = reverse('backend:buyer-detail', args=[buyer_id])
    response = client_with_credentials.get(url)
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json['name'] == pattern

@pytest.mark.django_db
def test_buyer_get_retrieve_403(client_with_credentials, user, user_2, model_factory):
    model_factory(Buyer, name='Покупатель 1', user=user)
    model_factory(Buyer, name='Покупатель 2', user=user)
    b3 = model_factory(Buyer, name='Покупатель 3', user=user_2)
    buyer_id = b3.id
    url = reverse('backend:buyer-detail', args=[buyer_id])
    response = client_with_credentials.get(url)
    response_json = response.json()

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response_json['detail'] == 'У вас недостаточно прав для выполнения данного действия.'

@pytest.mark.django_db
def test_buyer_post_201(client_with_credentials, user):
    url = reverse('backend:buyer-list')
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'locality_name': 'д.Тесто'}
    response = client_with_credentials.post(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_201_CREATED
    assert response_json['name'] == 'Т.Видео'
    assert response_json['user'] == user.id

def test_buyer_post_403(client_with_credentials, user):
    url = reverse('backend:buyer-list')
    user.type = 'supplier'
    user.save()
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'locality_name': 'д.Тесто'}
    response = client_with_credentials.post(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response_json['detail'] == 'У вас недостаточно прав для выполнения данного действия.'

@pytest.mark.django_db
def test_buyer_put_200(client_with_credentials, user, model_factory):
    buyer = model_factory(Buyer, name='Покупатель 1', region='Смоленская область', user=user)
    url = reverse('backend:buyer-detail', args=[buyer.id])
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'locality_name': 'д.Тесто'}
    response = client_with_credentials.put(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json['name'] == 'Т.Видео'
    assert response_json['region'] == 'Смоленская область'
    assert response_json['phone'] == '+79686325124'
    assert response_json['user'] == user.id

@pytest.mark.django_db
def test_buyer_patch_200(client_with_credentials, user, model_factory):
    buyer = model_factory(Buyer, name='Покупатель 1', region='Смоленская область', user=user)
    url = reverse('backend:buyer-detail', args=[buyer.id])
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'locality_name': 'д.Тесто'}
    response = client_with_credentials.patch(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json['name'] == 'Т.Видео'
    assert response_json['region'] == 'Смоленская область'
    assert response_json['phone'] == '+79686325124'
    assert response_json['user'] == user.id

@pytest.mark.django_db
def test_buyer_put_403(client_with_credentials, user, user_2, model_factory):
    buyer_1 = model_factory(Buyer, name='Покупатель 1', user=user)
    buyer_2 = model_factory(Buyer, name='Покупатель 2', user=user_2)
    buyer_id = buyer_2.id
    url = reverse('backend:buyer-detail', args=[buyer_id])
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124',
            'region': 'Смоленская область', 'locality_name': 'д.Тесто'}
    response = client_with_credentials.put(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response_json['detail'] == 'У вас недостаточно прав для выполнения данного действия.'

@pytest.mark.django_db
def test_buyer_delete_204(client_with_credentials, user, model_factory):
    buyer = model_factory(Buyer, name='Покупатель 1', user=user)
    buyer_id = buyer.id
    url = reverse('backend:buyer-detail', args=[buyer_id])
    response = client_with_credentials.delete(url)

    assert response.status_code == HTTP_204_NO_CONTENT
    assert not Buyer.objects.filter(id=buyer_id).first()

#___________________________________________________________________________________________________________

@pytest.mark.django_db
def test_supplier_get_list_200(client, user_s, user_s2, model_factory):
    # просматривать лист всех поставщиков может любой
    url = reverse('backend:supplier-list')
    model_factory(Supplier, name='Поставщик 1', user=user_s)
    model_factory(Supplier, name='Поставщик 2', user=user_s)
    model_factory(Supplier, name='Поставщик 3', user=user_s2)
    response = client.get(url)
    response_json = response.json()
    suppliers_names = [s['name'] for s in response_json["results"]]

    assert response.status_code == HTTP_200_OK
    assert response_json['count'] == 3
    assert ('Поставщик 1' and 'Поставщик 2' and 'Поставщик 3') in suppliers_names

@pytest.mark.django_db
def test_supplier_get_retrieve_200(client, user_s, model_factory):
    # просматривать отдельного поставщика может любой
    pattern = 'Поставщик 2'
    suppliers_names = ('Поставщик 1', 'Поставщик 2', 'Поставщик 3')
    suppliers = [model_factory(Supplier, name=name, user=user_s) for name in suppliers_names]
    supplier_id = next(s for s in suppliers if s.name == pattern).id
    url = reverse('backend:supplier-detail', args=[supplier_id])
    response = client.get(url)
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json['name'] == pattern

@pytest.mark.django_db
def test_supplier_post_201(client_with_credentials_user_s, user_s):
    url = reverse('backend:supplier-list')
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'locality_name': 'д.Тесто'}
    response = client_with_credentials_user_s.post(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_201_CREATED
    assert response_json['name'] == 'Т.Видео'
    assert response_json['user'] == user_s.id

def test_supplier_post_403(client_with_credentials, user):
    #  user c  type='buyer'
    url = reverse('backend:supplier-list')
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'locality_name': 'д.Тесто'}
    response = client_with_credentials.post(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response_json['detail'] == 'У вас недостаточно прав для выполнения данного действия.'


@pytest.mark.django_db
def test_supplier_put_200(client_with_credentials_user_s, user_s, model_factory):
    supplier = model_factory(Supplier, name='Поставщик 1', user=user_s)
    url = reverse('backend:supplier-detail', args=[supplier.id])
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'is_available': False}
    response = client_with_credentials_user_s.put(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json['name'] == 'Т.Видео'
    assert response_json['is_available'] == False
    assert response_json['user'] == user_s.id


@pytest.mark.django_db
def test_supplier_patch_200(client_with_credentials_user_s, user_s, model_factory):
    supplier = model_factory(Supplier, name='Поставщик 1', user=user_s)
    url = reverse('backend:supplier-detail', args=[supplier.id])
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'is_available': False}
    response = client_with_credentials_user_s.patch(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json['name'] == 'Т.Видео'
    assert response_json['is_available'] == False
    assert response_json['user'] == user_s.id


@pytest.mark.django_db
def test_supplier_put_403(client_with_credentials_user_s, user_s, user_s2, model_factory):
    supplier_1 = model_factory(Supplier, name='Поставщик 1', user=user_s)
    supplier_2 = model_factory(Supplier, name='Поставщик 2', user=user_s2)
    supplier_id = supplier_2.id
    url = reverse('backend:supplier-detail', args=[supplier_id])
    data = {'name': 'Т.Видео', 'person': 'Teсс Тина', 'phone': '+79686325124', 'is_available': False}
    response = client_with_credentials_user_s.put(url, data=data)
    response_json = response.json()

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response_json['detail'] == 'У вас недостаточно прав для выполнения данного действия.'


@pytest.mark.django_db
def test_supplier_delete_204(client_with_credentials_user_s, user_s, model_factory):
    supplier = model_factory(Supplier, name='Поставщик 1', user=user_s)
    supplier_id = supplier.id
    url = reverse('backend:supplier-detail', args=[supplier_id])
    response = client_with_credentials_user_s.delete(url)

    assert response.status_code == HTTP_204_NO_CONTENT
    assert not Supplier.objects.filter(id=supplier_id).first()

#___________________________________________________________________________________________________________


@pytest.mark.django_db
def test_place_order_200(client, user, get_token, model_factory):
    url = reverse('backend:buyer-order')
    token = get_token

    admin = model_factory(CustomUser, email='admin@test.ru', is_superuser=True, is_active=True)

    buyer1 = model_factory(Buyer, name='Покупатель 1', user=token.user)
    buyer2 = model_factory(Buyer, name='Покупатель 2', user=token.user)

    order1_id = model_factory(Order, buyer=buyer1).id
    order2_id = model_factory(Order, buyer=buyer2).id

    data = {'orders_ids': [order1_id, order2_id]}

    client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
    response = client.post(url, data)
    response_json = response.json()

    assert response_json == {'success': f'Успешное размещение: {{{order1_id}, {order2_id}}}'}
    assert Order.objects.get(id=order1_id).state == 'new'
    assert Order.objects.get(id=order1_id).state == 'new'

    # assert len(mail.outbox) == 4
    # assert mail.outbox[0].to == [user.email]
    # assert mail.outbox[1].to == [admin.email]
    # assert mail.outbox[0].subject == f'Успешное размещение заказа №{order1_id}'
    # assert mail.outbox[3].subject.split(',')[0] == f'Заказ №{order2_id}'
    # assert 'Детали заказа' in mail.outbox[1].body
    # assert 'Детали заказа' in mail.outbox[2].body
#___________________________________________________________________________________

@pytest.mark.django_db
def test_reset_password_200(client, user):

    url = reverse('backend:password-reset')
    email = user.email
    data = {'email': email}
    response = client.post(url, data=data)
    response_json = response.json()
    token_email = mail.outbox[0].body

    assert response.status_code == HTTP_200_OK
    assert response_json['status'] == 'OK'
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == 'Токен для сброса пароля'
    assert mail.outbox[0].body
    assert mail.outbox[0].to == [email]

    url = reverse('backend:password_reset-confirm')
    data = {'token': token_email, 'password': 'New_password_123'}
    response_2 = client.post(url, data=data)
    response_json_2 = response_2.json()

    user.refresh_from_db()

    assert response_2.status_code == HTTP_200_OK
    assert response_json_2['status'] == 'OK'
    assert user.check_password('New_password_123')

