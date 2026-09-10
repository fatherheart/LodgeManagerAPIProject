import pytest
from fastapi import status

from app.core.enums import RoomStatus
from test.conftest import base_url

room_url = f'{base_url}/rooms'


# =========================================================================
# 1. ROOM CREATION TESTS (STRICT AAA - ARRANGE VIA FIXTURES ONLY)
# =========================================================================

def test_operator_create_room_returns_200(authenticated_operator_client, pilot_room_schema, operator_pilot_lodge):
    """
    Tests that an active operator can create a room in their pilot lodge.
    """
    # Act
    response = authenticated_operator_client.post(url=room_url, json=pilot_room_schema.model_dump())
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert data['room_no'] == pilot_room_schema.room_no.lower()
    assert data['description'] == pilot_room_schema.description.lower()
    assert data['status'] == RoomStatus.VACANT
    assert data['base_rent_price'] == pilot_room_schema.base_rent_price
    assert data['lodge_id'] == operator_pilot_lodge.id
    assert 'id' in data
    assert 'created_at' in data


def test_create_duplicate_room_returns_400(authenticated_operator_client, pilot_lodge_room, pilot_room_schema):
    """
    Tests that creating a duplicate room number in the same lodge returns 400 RoomAlreadyExistError.
    """
    # Act (attempt to recreate the room that was already created by pilot_lodge_room fixture)
    response = authenticated_operator_client.post(url=room_url, json=pilot_room_schema.model_dump())
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert data['detail'] == f'Room: {pilot_lodge_room.room_no} already exists'


def test_tenant_cannot_create_room_returns_403(authenticated_tenant_client, pilot_room_schema):
    """
    Tests that a tenant cannot create a room and returns a 403 status code.
    """
    # Act
    response = authenticated_tenant_client.post(url=room_url, json=pilot_room_schema.model_dump())
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert data['detail'] == 'Only operators or landlords are allowed.'


def test_unassigned_operator_cannot_create_room_returns_404(authenticated_operator_client, mock_room_schema):
    """
    Tests that an operator cannot create a room in a lodge they are not assigned to (mock_room_schema belongs to landlord's lodge).
    """
    # Act
    response = authenticated_operator_client.post(url=room_url, json=mock_room_schema.model_dump())
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert data['detail'] == 'Lodge could not be found'


# =========================================================================
# 2. ROOM RETRIEVAL & PAGINATION (STRICT AAA)
# =========================================================================

def test_operator_get_room_details_by_id_returns_200(authenticated_operator_client, pilot_lodge_room, operator_pilot_lodge):
    """
    Tests that an active operator can get room details by ID.
    """
    # Act
    response = authenticated_operator_client.get(f'{room_url}/{pilot_lodge_room.id}')
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert data['room_no'] == pilot_lodge_room.room_no
    assert data['description'] == pilot_lodge_room.description
    assert data['base_rent_price'] == pilot_lodge_room.base_rent_price
    assert data['lodge_id'] == operator_pilot_lodge.id
    assert 'has_active_invite' in data
    assert 'pending_applicant' in data
    assert 'id' in data


def test_operator_get_rooms_returns_200(authenticated_operator_client, operator_pilot_lodge, pilot_rooms_batch):
    """
    Tests that an operator can list all rooms in their lodge.
    """
    # Act
    response = authenticated_operator_client.get(url=f'{room_url}/{operator_pilot_lodge.id}/rooms')
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(pilot_rooms_batch)


def test_get_rooms_pagination_limit_and_skip(authenticated_operator_client, operator_pilot_lodge, pilot_rooms_batch):
    """
    Tests pagination skip and limit for room listing.
    """
    # Act
    response = authenticated_operator_client.get(f'{room_url}/{operator_pilot_lodge.id}/rooms?skip=1&limit=2')
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    assert data[0]['room_no'] == pilot_rooms_batch[1].room_no


# =========================================================================
# 3. ROOM UPDATES & DOMAIN INVARIANTS (STRICT AAA)
# =========================================================================

@pytest.mark.parametrize("update_fields", [
    {"room_no": "new-rm-101"},
    {"description": "updated description for testing"},
    {"base_rent_price": 500000},
    {"room_no": "rm-202", "base_rent_price": 350000},
    {"description": "luxury suite", "status": RoomStatus.MAINTENANCE}
])
def test_operator_update_pilot_room_fields_returns_200(
    authenticated_operator_client, pilot_lodge_room, update_fields
):
    """
    Tests various valid field update combinations on an unclaimed pilot lodge room.
    """
    # Act
    response = authenticated_operator_client.patch(url=f'{room_url}/{pilot_lodge_room.id}', json=update_fields)
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    for key, value in update_fields.items():
        if isinstance(value, str):
            if isinstance(value, RoomStatus):
                assert data[key] == RoomStatus.MAINTENANCE
            else:
                assert data[key] == value.lower()
        else:
            assert data[key] == value


def test_operator_update_non_existent_room_returns_404(authenticated_operator_client, mock_update_room_schema):
    """
    Tests that updating a non-existent room returns a 404 status code.
    """
    # Act
    fake_room_id = 9999
    response = authenticated_operator_client.patch(
        url=f'{room_url}/{fake_room_id}',
        json=mock_update_room_schema.model_dump()
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Room could not be found'


def test_unassigned_operator_cannot_update_room_returns_404(
    authenticated_operator_client, other_landlord_room, mock_update_room_schema
):
    """
    Tests that an operator cannot update a room in a lodge they are not assigned to.
    """
    # Act
    response = authenticated_operator_client.patch(
        url=f'{room_url}/{other_landlord_room.id}',
        json=mock_update_room_schema.model_dump()
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Room could not be found'


def test_operator_cannot_update_occupied_room(authenticated_operator_client, pilot_active_lease):
    """
    Tests that updating an occupied room returns 400 RoomIsOccupiedError.
    """
    # Act
    room_id = pilot_active_lease.room_id
    response = authenticated_operator_client.patch(
        url=f'{room_url}/{room_id}',
        json={'status': RoomStatus.OCCUPIED}
    )
    data = response.json()
    print(data)

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert data['detail'] == 'Cannot update an occupied room. Terminate the lease first.'



def test_assigned_operator_cannot_update_base_rent_on_claimed_lodge_returns_403(
    authenticated_operator_client, hired_caretaker_room
):
    """
    Tests that an assigned operator CANNOT update base rent price on a claimed property (Only owner permitted).
    """
    # Act (Attempt to change base rent price on claimed lodge)
    response = authenticated_operator_client.patch(
        url=f'{room_url}/{hired_caretaker_room.id}',
        json={"base_rent_price": 999999}
    )

    # Assert
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'Only lodge owners are allowed' in response.json()['detail']



# =========================================================================
# 4. ONBOARDING STATE COMPLEX QUERY TESTS (STRICT AAA)
# =========================================================================

def test_operator_get_room_onboarding_state_pure_vacant_returns_200(
    authenticated_operator_client, pilot_lodge_room
):
    """
    Test a newly created vacant room has no active invite and no pending applicant.
    """
    # Act
    response = authenticated_operator_client.get(f'{room_url}/{pilot_lodge_room.id}')
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert data['has_active_invite'] is False
    assert data['pending_applicant'] is None


def test_operator_get_room_onboarding_state_active_unexpired_invite_returns_200(
    authenticated_operator_client, pilot_tenant_invite
):
    """
    Test a room with an unexpired SENT invite correctly reflects has_active_invite=True.
    """
    # Act
    room_id = pilot_tenant_invite.room_id
    response = authenticated_operator_client.get(f'{room_url}/{room_id}')
    data = response.json()

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert data['has_active_invite'] is True
    assert data['pending_applicant'] is None


def test_operator_get_room_onboarding_state_pending_applicant_returns_200(
    authenticated_operator_client, pilot_pending_tenant
):
    room_id = pilot_pending_tenant.invite.room_id
    response = authenticated_operator_client.get(f'{room_url}/{room_id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['pending_applicant'] is not None
    assert data['pending_applicant']['tenant_id'] == pilot_pending_tenant.id


# =========================================================================
# 5. BULK ROOM BASE RENT UPDATE TESTS (PATCH /rooms/{lodge_id}/rooms/bulk)
# =========================================================================

def test_owner_bulk_update_rooms_base_rent_returns_200(
    authenticated_operator_client, operator_pilot_lodge, pilot_vacant_rooms_pool
):
    room_ids = [r.id for r in pilot_vacant_rooms_pool[:2]]
    payload = {
        "room_ids": room_ids,
        "base_rent": 280000
    }
    response = authenticated_operator_client.patch(
        f'{room_url}/{operator_pilot_lodge.id}/rooms/bulk', json=payload
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == 2
    for room in data:
        assert room['base_rent_price'] == 280000


def test_assigned_non_owner_cannot_bulk_update_returns_403(
    authenticated_operator_client, hired_caretaker_room
):
    payload = {
        "room_ids": [hired_caretaker_room.id],
        "base_rent": 250000
    }
    response = authenticated_operator_client.patch(
        f'{room_url}/{hired_caretaker_room.lodge_id}/rooms/bulk', json=payload
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'Only lodge owners are allowed' in response.json()['detail']



def test_owner_cannot_bulk_update_occupied_room_returns_400(
    authenticated_operator_client, operator_pilot_lodge, pilot_active_lease
):
    payload = {
        "room_ids": [pilot_active_lease.room_id],
        "base_rent": 300000
    }
    response = authenticated_operator_client.patch(
        f'{room_url}/{operator_pilot_lodge.id}/rooms/bulk', json=payload
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "occupied room" in response.json()['detail'].lower()


def test_bulk_update_room_count_mismatch_returns_404(
    authenticated_operator_client, operator_pilot_lodge, pilot_lodge_room
):
    payload = {
        "room_ids": [pilot_lodge_room.id, 99999],
        "base_rent": 300000
    }
    response = authenticated_operator_client.patch(
        f'{room_url}/{operator_pilot_lodge.id}/rooms/bulk', json=payload
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "one or more rooms" in response.json()['detail'].lower()



