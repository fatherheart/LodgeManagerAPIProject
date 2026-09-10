from datetime import timedelta
import pytest
from fastapi import status

from app.core.enums import LeaseStatus, TenantStatus
from app.services import tenant_services
from test.conftest import base_url

lease_url = f'{base_url}/leases'


# =========================================================================
# 1. LEASE CREATION FOR EXISTING RESIDENTS (OPERATOR-FIRST & STRICT AAA)
# =========================================================================

def test_operator_create_lease_for_approved_existing_tenant_returns_200(
    test_db, authenticated_operator_client, operator_user, mock_lease_schema
):
    """
    Tests that an operator can create a lease for an APPROVED existing resident.
    """
    payload = mock_lease_schema.model_dump(mode='json')

    tenant = tenant_services.fetch_tenant_by_landlord(
        test_db, tenant_id=mock_lease_schema.tenant_id, current_user=operator_user
    )
    tenant.status = TenantStatus.APPROVED
    test_db.commit()

    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['tenant_id'] == mock_lease_schema.tenant_id
    assert data['room_id'] == mock_lease_schema.room_id
    assert data['agreed_rent_amt'] == mock_lease_schema.agreed_rent_amt
    assert data['status'] == 'Active'
    assert 'id' in data


def test_operator_cannot_create_direct_lease_for_pending_applicant_returns_400(
    authenticated_operator_client, mock_lease_schema
):
    """
    Tests that an operator cannot create a lease directly for a PENDING applicant (must onboard via invitation approval).
    """
    payload = mock_lease_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Onboard them via invitation approval instead' in data['detail']




def test_operator_create_lease_for_rejected_existing_tenant_returns_200_and_flips_status_to_approved(
    test_db, authenticated_operator_client, operator_user, mock_lease_schema
):
    """
    Tests that creating a lease for a REJECTED existing resident succeeds and atomically flips their status to APPROVED.
    """
    tenant = tenant_services.fetch_tenant_by_landlord(
        test_db, tenant_id=mock_lease_schema.tenant_id, current_user=operator_user
    )
    tenant.status = TenantStatus.REJECTED
    test_db.commit()

    payload = mock_lease_schema.model_dump(mode='json')
    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['tenant_id'] == mock_lease_schema.tenant_id
    assert data['status'] == 'Active'

    test_db.refresh(tenant)
    assert tenant.status == TenantStatus.APPROVED


def test_operator_create_lease_upfront_payment_exceeds_agreed_rent_returns_422(
    authenticated_operator_client, mock_lease_schema
):
    """
    Tests that Pydantic validation rejects upfront payment exceeding agreed rent amount.
    """
    payload = mock_lease_schema.model_dump(mode='json')
    payload['total_amt_paid'] = payload['agreed_rent_amt'] + 50000

    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert any("Upfront payment cannot exceed agreed rent amount" in err.get('msg', '') for err in data.get('detail', []))


def test_operator_create_lease_room_does_not_exist_returns_404(
    authenticated_operator_client, mock_lease_schema
):
    mock_lease_schema.room_id = 99999
    payload = mock_lease_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Room could not be found" in data['detail']


def test_unassigned_operator_create_lease_returns_404(
    authenticated_operator_client, mock_lease_schema, other_landlord_room
):
    mock_lease_schema.room_id = other_landlord_room.id
    payload = mock_lease_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Room could not be found" in data['detail']


def test_operator_create_lease_tenant_does_not_exist_returns_404(
    authenticated_operator_client, mock_lease_schema
):
    mock_lease_schema.tenant_id = 99999
    payload = mock_lease_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Tenantprofile could not be found" in data['detail']


def test_operator_create_lease_tenant_not_in_same_lodge_returns_404(
    authenticated_operator_client, mock_lease_schema, other_landlord_tenant
):
    mock_lease_schema.tenant_id = other_landlord_tenant.id
    payload = mock_lease_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(lease_url, json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Tenantprofile could not be found" in data['detail']


def test_operator_create_lease_room_already_has_active_lease_returns_400(
    authenticated_operator_client, mock_lease_schema, pilot_active_lease
):
    mock_lease_schema.room_id = pilot_active_lease.room_id

    lease_payload = mock_lease_schema.model_dump(mode='json')
    response = authenticated_operator_client.post(lease_url, json=lease_payload)
    data = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Lease is already Active" in data['detail']


# =========================================================================
# 2. LEASE RETRIEVAL & PAGINATION (OPERATOR-FIRST)
# =========================================================================

def test_operator_get_paginated_leases_returns_200(
    authenticated_operator_client, pilot_leases_pool, operator_pilot_lodge
):
    """
    Tests that an operator can get a list of all leases in their lodge.
    """
    lodge_id = operator_pilot_lodge.id
    response = authenticated_operator_client.get(f'{lease_url}/{lodge_id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(pilot_leases_pool)


def test_operator_get_leases_pagination_limit_returns_200(
    authenticated_operator_client, pilot_leases_pool, operator_pilot_lodge
):
    limit = 3
    lodge_id = operator_pilot_lodge.id
    response = authenticated_operator_client.get(f'{lease_url}/{lodge_id}?limit={limit}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == limit


def test_operator_get_leases_pagination_skip_returns_200(
    authenticated_operator_client, pilot_leases_pool, operator_pilot_lodge
):
    skip = 2
    limit = 3
    lodge_id = operator_pilot_lodge.id
    response = authenticated_operator_client.get(f'{lease_url}/{lodge_id}?skip={skip}&limit={limit}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == limit
    assert data[0]['id'] == pilot_leases_pool[skip].id


@pytest.mark.parametrize("status_filter", [
    LeaseStatus.ACTIVE,
    LeaseStatus.OVERDUE
])
def test_operator_get_leases_pagination_with_status_filter_returns_200(
    authenticated_operator_client, pilot_leases_pool, operator_pilot_lodge, status_filter
):
    lodge_id = operator_pilot_lodge.id
    response = authenticated_operator_client.get(f'{lease_url}/{lodge_id}?status={status_filter.value}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    expected_filtered_leases = [lease for lease in pilot_leases_pool if lease.status == status_filter]
    assert len(data) == len(expected_filtered_leases)

    for lease in data:
        assert lease['status'] == status_filter.value


def test_tenant_cannot_get_operator_gated_leases_returns_403(
    authenticated_tenant_client, operator_pilot_lodge
):
    lodge_id = operator_pilot_lodge.id
    response = authenticated_tenant_client.get(f'{lease_url}/{lodge_id}')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'


def test_unassigned_operator_cannot_get_leases_for_unassigned_lodge_returns_404(
    authenticated_operator_client, other_landlord_lodge
):
    lodge_id = other_landlord_lodge.id
    response = authenticated_operator_client.get(f'{lease_url}/{lodge_id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lodge could not be found'


# =========================================================================
# 3. TENANT PERSONAL LEASE ACCESS (/leases/tenant/me)
# =========================================================================

def test_tenant_get_own_lease_history_returns_200(
    auth_client_factory, pilot_tenant_lease_history
):
    tenant, db_leases = pilot_tenant_lease_history
    client = auth_client_factory(user_id=tenant.user_id)

    response = client.get(f'{lease_url}/tenant/me')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(db_leases)


def test_operator_cannot_get_tenant_personal_lease_history_returns_403(
    authenticated_operator_client
):
    response = authenticated_operator_client.get(f'{lease_url}/tenant/me')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only tenants are allowed.'


# =========================================================================
# 4. LEASE TERMINATION FLOWS (OPERATOR-FIRST & STRICT AAA)
# =========================================================================

def test_operator_terminate_active_lease_returns_200(
    authenticated_operator_client, pilot_active_lease
):
    """
    Tests that an operator can successfully terminate an ACTIVE lease.
    """
    lease_id = pilot_active_lease.id
    response = authenticated_operator_client.patch(f'{lease_url}/terminate/{lease_id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['status'] == LeaseStatus.TERMINATED.value
    assert data['end_date'] is not None


def test_operator_terminate_non_existent_lease_returns_404(
    authenticated_operator_client
):
    fake_lease_id = 9999
    response = authenticated_operator_client.patch(f'{lease_url}/terminate/{fake_lease_id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


def test_operator_terminate_already_terminated_lease_returns_400(
    authenticated_operator_client, pilot_terminated_lease
):
    lease = pilot_terminated_lease
    response = authenticated_operator_client.patch(f'{lease_url}/terminate/{lease.id}')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"Lease is already {lease.status.value}" in response.json()['detail']


def test_unassigned_operator_terminate_lease_returns_404(
    authenticated_operator_client, other_landlord_active_lease
):
    response = authenticated_operator_client.patch(f'{lease_url}/terminate/{other_landlord_active_lease.id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Lodge could not be found" in response.json()['detail']



# =========================================================================
# 5. TENANT LEASE TERMINATION APPEALS
# =========================================================================

def test_tenant_appeal_active_lease_returns_200(
    auth_client_factory, pilot_active_lease
):
    client = auth_client_factory(user_id=pilot_active_lease.tenant.user_id)
    response = client.patch(f'{lease_url}/me/terminate/{pilot_active_lease.id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['status'] == LeaseStatus.PENDING_TERMINATION.value


def test_tenant_appeal_non_existent_lease_returns_404(
    authenticated_tenant_client
):
    fake_lease_id = 9999
    response = authenticated_tenant_client.patch(f'{lease_url}/me/terminate/{fake_lease_id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


def test_tenant_appeal_lease_not_owned_returns_404(
    auth_client_factory, second_tenant_in_landlord_lodge, pilot_active_lease
):
    client = auth_client_factory(user_id=second_tenant_in_landlord_lodge.user_id)
    response = client.patch(f'{lease_url}/me/terminate/{pilot_active_lease.id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


@pytest.mark.parametrize("fixture_name", [
    "pilot_terminated_lease",
    "pilot_pending_termination_lease"
])
def test_tenant_appeal_invalid_status_lease_returns_400(
    auth_client_factory, request, fixture_name
):
    lease = request.getfixturevalue(fixture_name)
    client = auth_client_factory(user_id=lease.tenant.user_id)

    response = client.patch(f'{lease_url}/me/terminate/{lease.id}')
    data = response.json()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert data['detail'] == f"Lease is already {lease.status.value}"


# =========================================================================
# 6. ROUTE GATE CROSS-ROLE AUTHORIZATION TESTS
# =========================================================================

def test_tenant_cannot_create_lease_returns_403(
    authenticated_tenant_client, mock_lease_schema
):
    payload = mock_lease_schema.model_dump(mode='json')
    response = authenticated_tenant_client.post(lease_url, json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'


def test_tenant_cannot_terminate_lease_via_manager_endpoint_returns_403(
    authenticated_tenant_client, pilot_active_lease
):
    response = authenticated_tenant_client.patch(f'{lease_url}/terminate/{pilot_active_lease.id}')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'


def test_operator_cannot_appeal_for_termination_via_tenant_endpoint_returns_403(
    authenticated_operator_client, pilot_active_lease
):
    response = authenticated_operator_client.patch(f'{lease_url}/me/terminate/{pilot_active_lease.id}')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only tenants are allowed.'


# =========================================================================
# 7. LEASE UPDATE TESTS (PATCH /leases/{lease_id})
# =========================================================================

@pytest.mark.parametrize("update_payload, check_fields", [
    ({"agreed_rent_amt": 350000}, ["agreed_rent_amt"]),
    ({"end_date": "2027-06-30"}, ["end_date"]),
    ({"agreed_rent_amt": 400000, "end_date": "2027-12-31"}, ["agreed_rent_amt", "end_date"]),
])
def test_operator_update_lease_fields_returns_200(
    authenticated_operator_client, pilot_active_lease, update_payload, check_fields
):
    """
    Tests that an active operator can update specific or combined lease fields (rent, end date, both).
    """
    response = authenticated_operator_client.patch(
        f'{lease_url}/{pilot_active_lease.id}', json=update_payload
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    for field in check_fields:
        assert data[field] == update_payload[field]


@pytest.mark.parametrize("fixture_name", [
    "pilot_active_lease",
    "pilot_overdue_lease",
    "pilot_pending_termination_lease"
])
def test_operator_update_lease_across_valid_statuses_returns_200(
    authenticated_operator_client, request, fixture_name
):
    """
    Tests that an active operator can update lease terms across different active/pending lease statuses.
    """
    lease = request.getfixturevalue(fixture_name)
    payload = {"agreed_rent_amt": 380000}

    response = authenticated_operator_client.patch(f'{lease_url}/{lease.id}', json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['agreed_rent_amt'] == payload['agreed_rent_amt']


def test_operator_update_non_existent_lease_returns_404(
    authenticated_operator_client
):
    payload = {"agreed_rent_amt": 300000}
    response = authenticated_operator_client.patch(f'{lease_url}/99999', json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


@pytest.mark.parametrize("payload", [
    {"agreed_rent_amt": 300000},
    {"end_date": "2027-06-30"},
])
def test_unassigned_operator_cannot_update_lease_returns_404(
    authenticated_operator_client, other_landlord_active_lease, payload
):
    """
    Tests that an operator cannot update any fields of a lease in a lodge they are not assigned to.
    """
    response = authenticated_operator_client.patch(
        f'{lease_url}/{other_landlord_active_lease.id}', json=payload
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lodge could not be found'


def test_tenant_cannot_update_lease_returns_403(
    authenticated_tenant_client, pilot_active_lease
):
    """
    Tests that tenants are blocked at the route gate from updating lease terms.
    """
    payload = {"agreed_rent_amt": 100000}
    response = authenticated_tenant_client.patch(
        f'{lease_url}/{pilot_active_lease.id}', json=payload
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'


