import pytest
from fastapi import status
from app.core.enums import InviteStatus
from test.conftest import base_url

invite_url = f'{base_url}/invites'


# =========================================================================
# 1. INVITE CREATION TESTS (STRICT AAA & PARAMETRIZED)
# =========================================================================

def test_operator_create_invite_record_returns_201(
    authenticated_operator_client, invite_schema_factory, operator_pilot_lodge, pilot_lodge_room
):
    """
    Tests that an active operator can create an invite for a vacant room in their pilot lodge.
    """
    payload = invite_schema_factory(
        room_id=pilot_lodge_room.id,
        lodge_id=operator_pilot_lodge.id
    ).model_dump(mode='json')

    response = authenticated_operator_client.post(f'{invite_url}', json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data['lodge_id'] == operator_pilot_lodge.id
    assert data['room_id'] == pilot_lodge_room.id
    assert data['room_no'] == pilot_lodge_room.room_no
    assert data['status'] == InviteStatus.SENT
    assert 'id' in data


def test_operator_get_invite_by_id_returns_200(
    authenticated_operator_client, pilot_tenant_invite, operator_pilot_lodge
):
    """
    Tests that an invitation details can be retrieved by its ID.
    """
    invite_id = pilot_tenant_invite.id

    response = authenticated_operator_client.get(f'{invite_url}/{invite_id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['lodge_name'] == operator_pilot_lodge.name
    assert 'room_no' in data


def test_create_duplicate_invite_returns_existing_active_invite_idempotently(
    authenticated_operator_client, pilot_tenant_invite, invite_schema_factory
):
    """
    Tests that requesting an invite for a room that already has an active pending invitation
    idempotently returns the existing active invite.
    """
    room_id = pilot_tenant_invite.room_id
    payload = invite_schema_factory(
        room_id=room_id,
        lodge_id=pilot_tenant_invite.lodge_id
    ).model_dump(mode='json')

    response = authenticated_operator_client.post(f'{invite_url}', json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data['id'] == str(pilot_tenant_invite.id)
    assert data['room_id'] == room_id


def test_unassigned_operator_cannot_create_invite_returns_404(
    authenticated_operator_client, other_landlord_room, invite_schema_factory
):
    """
    Tests that an operator cannot create an invite for a room in a lodge they are not assigned to.
    """
    payload = invite_schema_factory(
        room_id=other_landlord_room.id,
        lodge_id=other_landlord_room.lodge_id
    ).model_dump(mode='json')

    response = authenticated_operator_client.post(f'{invite_url}', json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == "Room could not be found"



@pytest.mark.parametrize("room_fixture, expected_status_substr", [
    ("pilot_maintenance_rooms_pool", "Maintenance"),
    ("pilot_active_lease", "Occupied"),
])
def test_cannot_create_invite_for_non_vacant_room_returns_400(
    authenticated_operator_client, request, invite_schema_factory, operator_pilot_lodge,
    room_fixture, expected_status_substr
):
    """
    Tests that invitations cannot be issued for rooms that are not VACANT (e.g. MAINTENANCE or OCCUPIED).
    """
    fixture_val = request.getfixturevalue(room_fixture)
    room = fixture_val[0] if isinstance(fixture_val, list) else fixture_val.room

    payload = invite_schema_factory(
        room_id=room.id,
        lodge_id=operator_pilot_lodge.id
    ).model_dump(mode='json')

    response = authenticated_operator_client.post(f'{invite_url}', json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert expected_status_substr.lower() in response.json()['detail'].lower()



def test_tenant_cannot_create_invite_returns_403(
    authenticated_tenant_client, invite_schema_factory, pilot_lodge_room, operator_pilot_lodge
):
    """
    Tests that tenants are blocked at the route gate with 403 Forbidden.
    """
    payload = invite_schema_factory(
        room_id=pilot_lodge_room.id,
        lodge_id=operator_pilot_lodge.id
    ).model_dump(mode='json')

    response = authenticated_tenant_client.post(f'{invite_url}', json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'
