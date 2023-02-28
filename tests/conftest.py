import pytest
from model_bakery import baker
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from backend.models import CustomUser


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def inactive_user():
    return CustomUser.objects.create_user(email='test-ina@test.te', password='ina-12345Qwer')


@pytest.fixture
def user():
    return CustomUser.objects.create_user(email='test@test.te', password='1-12345Qwer', is_active=True)


@pytest.fixture
def user_2():
    return CustomUser.objects.create_user(email='test-2@test.te', password='2-12345Qwer', is_active=True)


@pytest.fixture
def user_s():
    return CustomUser.objects.create_user(email='test-s@test.te', password='s1-12345Qwer', is_active=True,
                                          type='supplier')


@pytest.fixture
def user_s2():
    return CustomUser.objects.create_user(email='test-s2@test.te', password='s2-12345Qwer', is_active=True,
                                          type='supplier')


@pytest.fixture
def client_with_credentials(db, user, client):
    client.force_authenticate(user=user)
    yield client
    client.force_authenticate(user=None)


@pytest.fixture
def client_with_credentials_user_s(db, user_s, client):
    client.force_authenticate(user=user_s)
    yield client
    client.force_authenticate(user=None)


@pytest.fixture
def model_factory():
    def factory(model, *args, **kwargs):
        return baker.make(model, *args, **kwargs)
    return factory


@pytest.fixture
def get_token(db, user):
    token, _ = Token.objects.get_or_create(user=user)
    return token


@pytest.fixture
def get_token_user_s(db, user_s):
    token, _ = Token.objects.get_or_create(user=user_s)
    return token
