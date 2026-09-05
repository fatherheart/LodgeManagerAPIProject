import time
import pytest
from fastapi import status

from app.core.enums import TenantStatus
from test.conftest import base_url

auth_url_base = f'{base_url}/auth'


@pytest.mark.parametrize("endpoint, schema_fixture_name, expected_role", [
    (f'{auth_url_base}/register/landlord', 'mock_landlord_schema', 'Landlord'),
    (f'{auth_url_base}/register/operator', 'mock_operator_schema', 'Operator'),
])
def test_register_user_returns_201(client, request, endpoint, schema_fixture_name, expected_role):
    """
    Tests that a user (landlord or operator) can be registered and returns a 201 status code.
    """
    schema = request.getfixturevalue(schema_fixture_name)
    response = client.post(endpoint, json=schema.model_dump())
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data['first_name'] == schema.first_name
    assert data['last_name'] == schema.last_name
    assert data['email'] == schema.email
    assert data['phone_no'] == schema.phone_no
    assert data['role'] == expected_role
    assert 'id' in data
    assert 'password' not in data


@pytest.mark.parametrize("endpoint, add_user_fixture_name, schema_fixture_name", [
    (f'{auth_url_base}/register/landlord', 'landlord_user', 'mock_landlord_schema'),
    (f'{auth_url_base}/register/operator', 'operator_user', 'mock_operator_schema'),
])
def test_register_existing_user_returns_400(client, request, endpoint, add_user_fixture_name, schema_fixture_name):
    """
    Tests that registering an existing user returns a 400 status code.
    """
    existing_user = request.getfixturevalue(add_user_fixture_name)
    schema = request.getfixturevalue(schema_fixture_name)

    response = client.post(endpoint, json=schema.model_dump())
    data = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert data['detail'] == f'User: {existing_user.email} already exists'


@pytest.mark.parametrize("endpoint, add_user_fixture_name, schema_fixture_name", [
    (f'{auth_url_base}/register/landlord', 'landlord_user', 'mock_landlord_schema'),
    (f'{auth_url_base}/register/operator', 'operator_user', 'mock_operator_schema'),
])
def test_register_user_with_case_insensitive_duplicate_email_returns_400(
    client, request, endpoint, add_user_fixture_name, schema_fixture_name
):
    """
    Tests that a user cannot register with an email that already exists, regardless of case.
    """
    existing_user = request.getfixturevalue(add_user_fixture_name)
    duplicate_schema = request.getfixturevalue(schema_fixture_name)
    duplicate_schema.email = existing_user.email.upper()

    response = client.post(endpoint, json=duplicate_schema.model_dump())

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()['detail'] == f'User: {existing_user.email} already exists'


@pytest.mark.parametrize("schema_fixture_name, add_user_fixture_name, expected_role", [
    ('mock_landlord_schema', 'landlord_user', 'Landlord'),
    ('mock_operator_schema', 'operator_user', 'Operator'),
])
def test_login_user_returns_200(client, request, schema_fixture_name, add_user_fixture_name, expected_role):
    """
    Tests that a user (landlord or operator) can log in and returns a 200 status code.
    """
    schema = request.getfixturevalue(schema_fixture_name)
    db_user = request.getfixturevalue(add_user_fixture_name)

    payload = {
        'username': schema.email,
        'password': schema.password
    }
    response = client.post(f'{auth_url_base}/login', data=payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['id'] == db_user.id
    assert data['role'] == expected_role


@pytest.mark.parametrize("username, password, error_detail, needs_db_user", [
    # Case 1: The user does NOT exist in the database. No fixture needed.
    ("non_existent_user@test.com", "any_password", "Invalid email or password.", False),

    # Case 2: The user DOES exist, but the password is wrong. Fixture is needed.
    ("landlord@test.com", "wrong_password", "Invalid email or password.", True),
])
def test_login_with_invalid_credentials_returns_401(client, username, password, error_detail, needs_db_user, landlord_user):
    """
    Tests that login fails with a 401 status code for various invalid credential combinations.
    """
    login_username = landlord_user.email if needs_db_user else username

    payload = {
        'username': login_username,
        'password': password
    }
    response = client.post(f'{auth_url_base}/login', data=payload)
    data = response.json()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert data['detail'] == error_detail


def test_register_tenant_returns_201(client, mock_tenant_schema, landlord_claimed_lodge):
    """
    Tests that a tenant can be registered and returns a 201 status code.
    """
    t_payload = mock_tenant_schema.model_dump(mode='json')

    response = client.post(f'{auth_url_base}/register/tenant', json=t_payload)
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data['tenant_type'] == mock_tenant_schema.tenant_info.tenant_type
    assert data['emergency_contact_name'] == mock_tenant_schema.tenant_info.emergency_contact_name
    assert data['emergency_contact_phone_no'] == mock_tenant_schema.tenant_info.emergency_contact_phone_no
    assert data['status'] == TenantStatus.PENDING
    assert 'id' in data
    assert 'user_id' in data
    assert data['user'] != {}


def test_get_me_returns_authenticated_user(authenticated_landlord_client, landlord_user):
    response = authenticated_landlord_client.get(f'{auth_url_base}/me')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['id'] == landlord_user.id
    assert data['role'] == 'Landlord'


def test_get_me_not_token_returns_401(client):
    response = client.get(f'{auth_url_base}/me')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_not_exist_returns_404(test_db, authenticated_landlord_client, landlord_user):
    test_db.delete(landlord_user)
    test_db.commit()

    response = authenticated_landlord_client.get(f'{auth_url_base}/me')
    assert response.status_code == status.HTTP_404_NOT_FOUND



def test_logout_authenticated_user_returns_200(authenticated_landlord_client):
    response = authenticated_landlord_client.post(f'{auth_url_base}/logout')

    assert response.status_code == status.HTTP_200_OK
    cookies = response.headers.get('set-cookie')

    assert 'access_token=""' in cookies
    assert 'refresh_token=""' in cookies
    assert 'Max-Age' in cookies


def test_refresh_after_logout_returns_401(authenticated_landlord_client):
    authenticated_landlord_client.post(f'{auth_url_base}/logout')

    response = authenticated_landlord_client.post(f'{auth_url_base}/refresh')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_reusing_old_refresh_token_returns_401(authenticated_landlord_client):
    first_refresh_token = authenticated_landlord_client.cookies.get('refresh_token')

    time.sleep(1)

    response1 = authenticated_landlord_client.post(f'{auth_url_base}/refresh')
    assert response1.status_code == status.HTTP_200_OK

    response2 = authenticated_landlord_client.post(
        f'{auth_url_base}/refresh',
        cookies={"refresh_token": first_refresh_token}
    )

    assert response2.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_unauthenticated_returns_401(client):
    response = client.post(f'{auth_url_base}/logout')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

