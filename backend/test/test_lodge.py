import pytest
from fastapi import status

from app.core.enums import TenantStatus
from app.services import lodge_service, room_service, invite_service
from test.conftest import base_url
from test.test_room import room_url

lodge_url = f'{base_url}/lodges'


# =========================================================================
# 1. LODGE REGISTRATION (PARAMETRIZED: LANDLORD CLAIMED VS OPERATOR PILOT)
# =========================================================================

@pytest.mark.parametrize("endpoint, client_fixture, is_claimed", [
    (f'{lodge_url}/register', 'authenticated_landlord_client', True),
    (f'{lodge_url}/register/operator-pilot', 'authenticated_operator_client', False),
])
def test_register_lodge_returns_200(request, endpoint, client_fixture, is_claimed, mock_lodge_schema):
    """
    Tests that a user (landlord or operator) can register a lodge.
    - Landlord creates a claimed lodge (landlord_id set).
    - Operator creates an unclaimed pilot lodge (landlord_id is None).
    """
    auth_client = request.getfixturevalue(client_fixture)
    payload = mock_lodge_schema.model_dump()

    response = auth_client.post(endpoint, json=payload)
    data = response.json()
    print(data)

    assert response.status_code == status.HTTP_200_OK
    assert data['name'] == mock_lodge_schema.name
    assert data['address'] == mock_lodge_schema.address
    assert 'id' in data

    if is_claimed:
        assert data['landlord_id'] == auth_client.user.id
    else:
        assert data.get('landlord_id') is None


@pytest.mark.parametrize("endpoint, client_fixture, add_lodge_fixture", [
    (f'{lodge_url}/register', 'authenticated_landlord_client', 'landlord_claimed_lodge'),
    (f'{lodge_url}/register/operator-pilot', 'authenticated_operator_client', 'operator_pilot_lodge'),
])
def test_register_duplicate_lodge_returns_400(request, endpoint, client_fixture, add_lodge_fixture, mock_lodge_schema):
    """
    Tests that registering a duplicate lodge for the same user returns a 400 status code.
    """
    auth_client = request.getfixturevalue(client_fixture)
    existing_lodge = request.getfixturevalue(add_lodge_fixture)

    payload = mock_lodge_schema.model_dump()
    response = auth_client.post(endpoint, json=payload)
    data = response.json()
    print(data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert data['detail'] == f'Lodge: {existing_lodge.name} already exists'


def test_tenant_cannot_register_lodge_returns_403(authenticated_tenant_client, mock_lodge_schema):
    """
    Tests that a tenant cannot register a lodge and returns a 403 status code.
    """
    payload = mock_lodge_schema.model_dump()
    response = authenticated_tenant_client.post(f'{lodge_url}/register', json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert data['detail'] == 'Only landlords are allowed.'



@pytest.mark.parametrize('endpoint, client_fixture, last_room_number, is_claimed', [
    (f'{lodge_url}/register','authenticated_landlord_client', 5, True ),
    (f'{lodge_url}/register/operator-pilot','authenticated_operator_client', 8, False)
]

)
def test_user_create_lodge_with_rooms(test_db, request, endpoint, client_fixture,
                                      last_room_number, lodge_schema_with_room_generator_factory, is_claimed):
    """
    Tests that a landlord can register a lodge with pre-generated rooms.
    """
    lodge_schema = lodge_schema_with_room_generator_factory(end_number=last_room_number)

    auth_client = request.getfixturevalue(client_fixture)

    response = auth_client.post(endpoint, json=lodge_schema.model_dump())
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['name'] == lodge_schema.name
    assert data['address'] == lodge_schema.address
    assert 'id' in data


    if is_claimed:
        assert data['landlord_id'] == auth_client.user.id
    else:
        assert data.get('landlord_id') is None

    from app.crud.room import crud_room
    total_stored_rooms_in_db = len(crud_room.get_rooms(test_db, lodge_id=data['id']))
    assert total_stored_rooms_in_db == last_room_number




def test_get_landlord_lodges_returns_200(authenticated_landlord_client, landlord_portfolio_lodges):
    """
    Tests that a landlord can get a list of all their owned lodges and returns a 200 status code.
    """
    response = authenticated_landlord_client.get(f'{lodge_url}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(landlord_portfolio_lodges)


# =========================================================================
# 2. OPERATIONAL LODGE DETAILS & UPDATES (OPERATOR-FIRST)
# =========================================================================

def test_operator_get_lodge_by_id_returns_200(authenticated_operator_client, operator_pilot_lodge):
    """
    Tests that an active operator can get their lodge by ID and returns a 200 status code.
    """
    response = authenticated_operator_client.get(f'{lodge_url}/{operator_pilot_lodge.id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['name'] == operator_pilot_lodge.name
    assert data['address'] == operator_pilot_lodge.address
    assert data['id'] == operator_pilot_lodge.id
    assert data['is_active'] == operator_pilot_lodge.is_active


def test_operator_get_lodge_id_not_exist_returns_404(authenticated_operator_client):
    """
    Tests that getting a lodge with a non-existent ID returns a 404 status code.
    """
    fake_lodge_id = 9999
    response = authenticated_operator_client.get(f'{lodge_url}/{fake_lodge_id}')
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert data['detail'] == 'Lodge could not be found'


def test_unassigned_operator_get_lodge_returns_404(authenticated_operator_client, landlord_claimed_lodge):
    """
    Tests that an operator cannot access a lodge they are not assigned to and returns a 404 status code.
    """
    response = authenticated_operator_client.get(f'{lodge_url}/{landlord_claimed_lodge.id}')
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert data['detail'] == 'Lodge could not be found'


@pytest.mark.parametrize("update_payload, expected_name, expected_address", [
    # Scenario 1: Update name only
    ({"name": "New Pilot Name"}, "new pilot name", "test address"),
    # Scenario 2: Update address only
    ({"address": "New Pilot Address"}, "lodge test", "New Pilot Address"),
    # Scenario 3: Update both name and address
    ({"name": "Updated Name", "address": "Updated Address"}, "updated name", "Updated Address"),
])
def test_operator_update_unclaimed_lodge_scenarios(
    authenticated_operator_client,
    operator_pilot_lodge,
    update_payload,
    expected_name,
    expected_address
):
    """
    Tests various valid scenarios for an operator updating an unclaimed pilot lodge.
    """
    lodge_id = operator_pilot_lodge.id
    response = authenticated_operator_client.patch(f'{lodge_url}/{lodge_id}', json=update_payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['name'] == expected_name.lower()
    assert data['address'] == expected_address.lower()
    assert data['id'] == lodge_id


def test_operator_update_non_existent_lodge_returns_404(authenticated_operator_client, mock_update_lodge_schema):
    """
    Tests that an operator cannot update a non-existent lodge.
    """
    fake_lodge_id = 9999
    response = authenticated_operator_client.patch(f'{lodge_url}/{fake_lodge_id}', json=mock_update_lodge_schema.model_dump())
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert data['detail'] == 'Lodge could not be found'


def test_assigned_operator_cannot_update_claimed_lodge_returns_403(
    authenticated_operator_client, hired_caretaker_claimed_lodge, mock_update_lodge_schema
):
    """
    Tests that an operator assigned to a claimed lodge CANNOT update lodge details (Reserved for owner).
    """
    # Act
    response = authenticated_operator_client.patch(
        f'{lodge_url}/{hired_caretaker_claimed_lodge.id}',
        json=mock_update_lodge_schema.model_dump()
    )

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'Only lodge owners are allowed' in response.json()['detail']


# =========================================================================
# 3. OPERATIONAL TENANT MANAGEMENT IN LODGE (OPERATOR-FIRST)
# =========================================================================

def test_operator_get_paginated_tenants_returns_200(
    authenticated_operator_client, operator_pilot_lodge, pilot_pending_tenants_batch
):
    """
    Tests that an operator can get a list of tenants in their lodge.
    """
    # Act
    response = authenticated_operator_client.get(f'{lodge_url}/{operator_pilot_lodge.id}/tenants')
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(pilot_pending_tenants_batch)
    assert data[0]['user']['email'] == pilot_pending_tenants_batch[0].user.email


def test_operator_get_tenants_from_non_existent_lodge_returns_404(authenticated_operator_client):
    """
    Tests that an operator cannot get tenants from a lodge that does not exist.
    """
    # Act
    fake_lodge_id = 9999
    response = authenticated_operator_client.get(f'{lodge_url}/{fake_lodge_id}/tenants')
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert data['detail'] == 'Lodge could not be found'


