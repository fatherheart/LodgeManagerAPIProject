import pytest
from fastapi import status

from app.core.enums import LeaseStatus
from test.conftest import base_url

payment_url = f'{base_url}/payments'


# =========================================================================
# 1. CREATE PAYMENT TESTS (OPERATOR-FIRST & STRICT AAA)
# =========================================================================

def test_operator_create_payment_returns_200(
    authenticated_operator_client, pilot_active_lease, mock_payment_schema
):
    """
    Tests that an active operator can successfully record a rent payment for an active lease.
    """
    mock_payment_schema.lease_id = pilot_active_lease.id
    payload = mock_payment_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(f'{payment_url}/create-payment', json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['amount_paid'] == mock_payment_schema.amount_paid
    assert data['lease_id'] == mock_payment_schema.lease_id
    assert 'id' in data
    assert 'payment_date' in data


def test_operator_create_payment_lease_does_not_exist_returns_404(
    authenticated_operator_client, mock_payment_schema
):
    mock_payment_schema.lease_id = 99999
    payload = mock_payment_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(f'{payment_url}/create-payment', json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


def test_unassigned_operator_create_payment_returns_404(
    authenticated_operator_client, mock_payment_schema, other_landlord_active_lease
):
    """
    Tests that an operator cannot record a payment for a lease in a lodge they are not assigned to.
    """
    mock_payment_schema.lease_id = other_landlord_active_lease.id
    payload = mock_payment_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(f'{payment_url}/create-payment', json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lodge could not be found'


@pytest.mark.parametrize("fixture_name", [
    "pilot_overdue_lease",
    "pilot_active_lease",
    "pilot_pending_termination_lease"
])
def test_operator_create_payment_for_valid_lease_statuses_returns_200(
    authenticated_operator_client, request, fixture_name
):
    """
    Tests that an operator can record payments for valid lease statuses (Active, Overdue, Pending Termination).
    """
    lease = request.getfixturevalue(fixture_name)
    payload = {
        "amount_paid": 5000,
        "lease_id": lease.id
    }
    response = authenticated_operator_client.post(f'{payment_url}/create-payment', json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['amount_paid'] == payload['amount_paid']
    assert data['lease_id'] == lease.id
    assert 'id' in data


def test_operator_create_payment_for_terminated_lease_returns_400(
    authenticated_operator_client, pilot_terminated_lease
):
    lease = pilot_terminated_lease
    payload = {
        "amount_paid": 5000,
        "lease_id": lease.id
    }
    response = authenticated_operator_client.post(f'{payment_url}/create-payment', json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f'Lease is already {LeaseStatus.TERMINATED.value}' in response.json()['detail']


def test_operator_create_payment_exceeds_agreed_rent_returns_400(
    authenticated_operator_client, mock_payment_schema, pilot_active_lease
):
    mock_payment_schema.lease_id = pilot_active_lease.id
    mock_payment_schema.amount_paid = pilot_active_lease.agreed_rent_amt + 1000
    payload = mock_payment_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(f'{payment_url}/create-payment', json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Remaining balance is" in response.json()['detail']


def test_operator_create_payment_negative_amount_returns_422(
    authenticated_operator_client, mock_payment_schema, pilot_active_lease
):
    mock_payment_schema.lease_id = pilot_active_lease.id
    mock_payment_schema.amount_paid = -5000
    payload = mock_payment_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(f'{payment_url}/create-payment', json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_tenant_cannot_create_payment_returns_403(
    authenticated_tenant_client, mock_payment_schema, pilot_active_lease
):
    mock_payment_schema.lease_id = pilot_active_lease.id
    payload = mock_payment_schema.model_dump(mode='json')

    response = authenticated_tenant_client.post(f'{payment_url}/create-payment', json=payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'


# =========================================================================
# 2. LIST LEASE PAYMENTS TESTS (OPERATOR-FIRST)
# =========================================================================

def test_operator_get_lease_payments_returns_200(
    authenticated_operator_client, pilot_multiple_safe_payments
):
    db_payments, lease = pilot_multiple_safe_payments
    response = authenticated_operator_client.get(f'{payment_url}/{lease.id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(db_payments)


def test_operator_get_lease_payments_pagination_limit(
    authenticated_operator_client, pilot_multiple_safe_payments
):
    db_payments, lease = pilot_multiple_safe_payments
    limit = 3
    response = authenticated_operator_client.get(f'{payment_url}/{lease.id}?limit={limit}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == limit


def test_operator_get_lease_payments_pagination_skip(
    authenticated_operator_client, pilot_multiple_safe_payments
):
    db_payments, lease = pilot_multiple_safe_payments
    skip = 2
    limit = 2
    response = authenticated_operator_client.get(f'{payment_url}/{lease.id}?skip={skip}&limit={limit}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == limit
    assert data[0]['id'] == db_payments[skip].id


def test_operator_get_payments_lease_does_not_exist_returns_404(
    authenticated_operator_client
):
    fake_lease_id = 9999
    response = authenticated_operator_client.get(f'{payment_url}/{fake_lease_id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


def test_unassigned_operator_get_payments_not_assigned_lodge_returns_404(
    authenticated_operator_client, other_landlord_active_lease
):
    lease_id = other_landlord_active_lease.id
    response = authenticated_operator_client.get(f'{payment_url}/{lease_id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lodge could not be found'


# =========================================================================
# 3. LIST TENANT PAYMENTS (SELF-SERVICE VIA /payments/me/{lease_id})
# =========================================================================

def test_tenant_get_own_lease_payments_returns_200(
    auth_client_factory, pilot_tenant_safe_payments
):
    db_payments, lease = pilot_tenant_safe_payments
    client = auth_client_factory(user_id=lease.tenant.user_id)

    response = client.get(f'{payment_url}/me/{lease.id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == len(db_payments)


def test_tenant_get_own_lease_payments_pagination_limit(
    auth_client_factory, pilot_tenant_safe_payments
):
    db_payments, lease = pilot_tenant_safe_payments
    client = auth_client_factory(user_id=lease.tenant.user_id)
    limit = 2

    response = client.get(f'{payment_url}/me/{lease.id}?limit={limit}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == limit


def test_tenant_get_own_lease_payments_pagination_skip(
    auth_client_factory, pilot_tenant_safe_payments
):
    db_payments, lease = pilot_tenant_safe_payments
    client = auth_client_factory(user_id=lease.tenant.user_id)
    skip = 1
    limit = 3

    response = client.get(f'{payment_url}/me/{lease.id}?skip={skip}&limit={limit}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data) == limit
    assert data[0]['id'] == db_payments[skip].id


def test_tenant_get_payments_lease_does_not_exist_returns_404(
    authenticated_tenant_client
):
    fake_lease_id = 9999
    response = authenticated_tenant_client.get(f'{payment_url}/me/{fake_lease_id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


def test_tenant_get_other_tenants_payments_returns_404(
    auth_client_factory, second_tenant_in_landlord_lodge, pilot_tenant_safe_payments
):
    db_payments, lease = pilot_tenant_safe_payments
    client = auth_client_factory(user_id=second_tenant_in_landlord_lodge.user_id)

    response = client.get(f'{payment_url}/me/{lease.id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


def test_operator_cannot_hit_tenant_payments_endpoint_returns_403(
    authenticated_operator_client, pilot_active_lease
):
    response = authenticated_operator_client.get(f'{payment_url}/me/{pilot_active_lease.id}')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only tenants are allowed.'
