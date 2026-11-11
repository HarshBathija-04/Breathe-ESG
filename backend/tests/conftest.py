import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Seed the test database once with the real sample-data pipeline."""
    with django_db_blocker.unblock():
        call_command('seed_db', verbosity=0)


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


def _login(client, email, password):
    res = client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')
    assert res.status_code == 200, res.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
    return client


@pytest.fixture
def analyst(db):
    return _login(APIClient(), 'analyst@democorp.com', 'analyst123')


@pytest.fixture
def reviewer(db):
    return _login(APIClient(), 'reviewer@democorp.com', 'reviewer123')
