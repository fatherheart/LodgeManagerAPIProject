from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi import status

from app.core.enums import TenantStatus
from app.services import lease_services, room_service, invite_service
from test.conftest import base_url

tenant_url = f'{base_url}/tenants'


# =========================================================================
# 1. TENANT PROFILE READ & UPDATE TESTS (SELF-SERVICE VIA STRICT AAA)
# =========================================================================

def test_tenant_get_personal_details_returns_200(
    authenticated_tenant_client, pilot_pending_tenant
):
    """
    Tests that a tenant can retrieve their own personal details via /profile.
    """
    response = authenticated_tenant_client.get(f'{tenant_url}/profile')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['id'] == pilot_pending_tenant.id
    assert data['user_id'] == pilot_pending_tenant.user_id
    assert data['tenant_type'] == pilot_pending_tenant.tenant_type


@pytest.mark.parametrize("update_payload, field_to_check, expected_value", [
    ({'user_info': {"first_name": "John"}}, "first_name", "John"),
    ({'user_info': {"last_name": "Doe"}}, "last_name", "Doe"),
    ({'user_info': {"phone_no": "1234567890"}}, "phone_no", "1234567890"),
    ({'tenant_info': {"emergency_contact_name": "Jane Doe"}}, "emergency_contact_name", "Jane Doe"),
    ({'tenant_info': {"emergency_contact_phone_no": "0987654321"}}, "emergency_contact_phone_no", "0987654321"),
])
def test_tenant_can_update_own_profile_returns_200(
    authenticated_tenant_client, update_payload, field_to_check, expected_value
):
    """
    Tests that a tenant can update their own core profile details.
    """
    response = authenticated_tenant_client.patch(f'{tenant_url}/profiles/me', json=update_payload)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK

    normalized_expected_value = expected_value.lower() if isinstance(expected_value, str) else expected_value

    if field_to_check not in data and 'user' in data:
        actual_data_value = data['user'].get(field_to_check)
        assert actual_data_value == normalized_expected_value
    else:
        actual_data_value = data.get(field_to_check)
        assert actual_data_value == normalized_expected_value


def test_tenant_get_other_tenant_profile_returns_403(
    authenticated_tenant_client, second_tenant_in_landlord_lodge
):
    """
    Tests that a tenant cannot get another tenant's profile details.
    """
    response = authenticated_tenant_client.get(f'{tenant_url}/profile/{second_tenant_in_landlord_lodge.id}')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'


def test_operator_cannot_hit_tenant_me_endpoint_returns_403(
    authenticated_operator_client
):
    """
    Tests that an operator trying to access the tenant's '/profiles/me' endpoint is forbidden.
    """
    update_payload = {"level": "LEVEL_300"}
    response = authenticated_operator_client.patch(f'{tenant_url}/profiles/me', json=update_payload)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only tenants are allowed.'


# =========================================================================
# 2. OPERATOR TENANT RETRIEVAL (STRICT AAA & ASSIGNMENT CHECK)
# =========================================================================

def test_operator_get_tenant_profile_returns_200(
    authenticated_operator_client, pilot_pending_tenant
):
    """
    Tests that an active operator can get the profile of a tenant in their lodge.
    """
    response = authenticated_operator_client.get(f'{tenant_url}/profile/{pilot_pending_tenant.id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['id'] == pilot_pending_tenant.id
    assert data['user_id'] == pilot_pending_tenant.user_id
    assert data['tenant_type'] == pilot_pending_tenant.tenant_type


def test_operator_get_tenant_profile_wrong_lodge_returns_404(
    authenticated_operator_client, other_landlord_tenant
):
    """
    Tests that an operator cannot get a tenant profile from a lodge they are not assigned to.
    """
    response = authenticated_operator_client.get(f'{tenant_url}/profile/{other_landlord_tenant.id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lodge could not be found'


def test_operator_get_non_existing_tenant_profile_returns_404(
    authenticated_operator_client
):
    fake_tenant_id = 99999
    response = authenticated_operator_client.get(f'{tenant_url}/profile/{fake_tenant_id}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Tenantprofile could not be found'


# =========================================================================
# 3. APPLICANT REJECTION FLOWS (STRICT AAA)
# =========================================================================

def test_operator_reject_pending_applicant_returns_200(
    authenticated_operator_client, pilot_pending_tenant
):
    """
    Tests that an operator can successfully reject a PENDING applicant.
    """
    tenant_id = pilot_pending_tenant.id

    response = authenticated_operator_client.post(f'{tenant_url}/{tenant_id}/reject')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data['id'] == tenant_id
    assert data['status'] == TenantStatus.REJECTED


@pytest.mark.parametrize("initial_status, expected_error_status", [
    (TenantStatus.APPROVED, "Approved"),
    (TenantStatus.REJECTED, "Rejected"),
])
def test_operator_cannot_reject_non_pending_applicant_returns_400(
    test_db, authenticated_operator_client, pilot_pending_tenant, initial_status, expected_error_status
):
    """
    Tests that attempting to reject an applicant whose status is not PENDING raises a 400 error.
    """
    tenant = pilot_pending_tenant
    tenant.status = initial_status
    test_db.commit()

    response = authenticated_operator_client.post(f'{tenant_url}/{tenant.id}/reject')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"Tenant Status is already {expected_error_status}" in response.json()['detail']



def test_operator_cannot_reject_non_existent_applicant_id_returns_404(
    authenticated_operator_client
):
    fake_tenant_id = 99999
    response = authenticated_operator_client.post(f'{tenant_url}/{fake_tenant_id}/reject')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Tenantprofile could not be found" in response.json()['detail']


def test_operator_cannot_reject_applicant_in_diff_lodge_returns_404(
    authenticated_operator_client, other_landlord_tenant
):
    response = authenticated_operator_client.post(f'{tenant_url}/{other_landlord_tenant.id}/reject')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Lodge could not be found" in response.json()['detail']


# =========================================================================
# 4. APPLICANT APPROVAL & ONBOARDING FLOWS (STRICT AAA & ATOMIC LEASE)
# =========================================================================

@pytest.mark.parametrize("initial_status, expected_error_status", [
    (TenantStatus.APPROVED, "Approved"),
    (TenantStatus.REJECTED, "Rejected"),
])
def test_operator_cannot_approve_non_pending_applicant_returns_400(
    test_db, authenticated_operator_client, pilot_pending_tenant, mock_tenant_approval_schema,
    initial_status, expected_error_status
):
    """
    Tests that an applicant whose status is not PENDING (i.e. already APPROVED or REJECTED)
    cannot be approved via the onboarding route.
    """
    tenant = pilot_pending_tenant
    tenant.status = initial_status
    test_db.commit()

    payload = mock_tenant_approval_schema.model_dump(mode='json')
    response = authenticated_operator_client.post(f'{tenant_url}/{tenant.id}/approve', json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"Tenant Status is already {expected_error_status}" in response.json()['detail']


def test_operator_approve_invited_tenant_application_creates_lease_and_occupies_room_returns_201(
    authenticated_operator_client, pilot_pending_tenant, mock_tenant_approval_schema
):
    """
    Tests that an operator can successfully approve a PENDING applicant, creating a lease and occupying the room.
    """
    tenant_id = pilot_pending_tenant.id
    payload = mock_tenant_approval_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(f'{tenant_url}/{tenant_id}/approve', json=payload)
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data['tenant_id'] == tenant_id
    assert 'id' in data
    assert data['agreed_rent_amt'] == mock_tenant_approval_schema.agreed_rent_amt


def test_operator_cannot_approve_non_existent_applicant_id_returns_404(
    authenticated_operator_client, mock_tenant_approval_schema
):
    fake_tenant_id = 99999
    payload = mock_tenant_approval_schema.model_dump(mode='json')

    response = authenticated_operator_client.post(f'{tenant_url}/{fake_tenant_id}/approve', json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Tenantprofile could not be found" in response.json()['detail']


def test_operator_cannot_approve_applicant_in_diff_lodge_returns_404(
    authenticated_operator_client, other_landlord_tenant, mock_tenant_approval_schema
):
    payload = mock_tenant_approval_schema.model_dump(mode='json')
    response = authenticated_operator_client.post(f'{tenant_url}/{other_landlord_tenant.id}/approve', json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Lodge could not be found" in response.json()['detail']


def test_operator_cannot_approve_applicant_if_room_already_occupied_returns_400(
    test_db, authenticated_operator_client, pilot_pending_tenant,
    mock_tenant_approval_schema, lease_schema_factory, operator_user, pilot_pending_tenants_pool
):
    """
    Tests that an operator cannot approve an applicant if the room has already become occupied by another tenant.
    """
    second_tenant = pilot_pending_tenants_pool[1]
    second_tenant.status = TenantStatus.APPROVED
    test_db.commit()

    room_id = pilot_pending_tenant.invite.room_id
    lease_data = lease_schema_factory(tenant_id=second_tenant.id, room_id=room_id)
    lease_services.create_new_lease_for_existing_tenant(test_db, lease_data=lease_data, current_user=operator_user)

    payload = mock_tenant_approval_schema.model_dump(mode='json')
    response = authenticated_operator_client.post(f'{tenant_url}/{pilot_pending_tenant.id}/approve', json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Lease is already Active" in response.json()['detail']


def test_operator_approve_applicant_with_overpayment_returns_422(
    authenticated_operator_client, pilot_pending_tenant, mock_tenant_approval_schema
):
    """
    Tests that approving an applicant with total amount paid exceeding agreed rent fails with 422.
    """
    payload = mock_tenant_approval_schema.model_dump(mode='json')
    payload['total_amt_paid'] = payload['agreed_rent_amt'] + 50000

    response = authenticated_operator_client.post(
        f'{tenant_url}/{pilot_pending_tenant.id}/approve', json=payload
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "Upfront payment cannot exceed agreed rent amount" in response.text



# =========================================================================
# 5. PUBLIC TENANT REGISTRATION VIA INVITE TESTS
# =========================================================================


def test_tenant_signup_with_expired_invite_returns_400(
    client, test_db, tenant_schema_factory, invite_schema_factory, operator_user, operator_pilot_lodge, room_schema_factory
):
    rm_schema = room_schema_factory(lodge_id=operator_pilot_lodge.id, room_no="Expired Invite Sign-up Rm")
    room = room_service.create_room_for_lodge(test_db, room_in=rm_schema, current_user=operator_user)

    expired_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
    inv_schema = invite_schema_factory(room_id=room.id, lodge_id=operator_pilot_lodge.id, expires_at=expired_date)
    invite = invite_service.invite_tenant(test_db, invite_in=inv_schema, current_user=operator_user)

    t_schema = tenant_schema_factory(email="expired_signup@test.com", invite_id=invite.id)
    response = client.post(f'{base_url}/auth/register/tenant', json=t_schema.model_dump(mode='json'))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invite is already Expired" in response.json()['detail']


def test_tenant_signup_with_already_accepted_invite_returns_400(
    client, pilot_pending_tenant, tenant_schema_factory
):
    accepted_invite_id = pilot_pending_tenant.invite.id
    t_schema = tenant_schema_factory(email="second_signup@test.com", invite_id=accepted_invite_id)

    response = client.post(f'{base_url}/auth/register/tenant', json=t_schema.model_dump(mode='json'))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invite is already Accepted" in response.json()['detail']


def test_tenant_signup_with_non_existent_invite_returns_404(
    client, tenant_schema_factory
):
    fake_invite_id = uuid.uuid4()
    t_schema = tenant_schema_factory(email="fake_invite@test.com", invite_id=fake_invite_id)

    response = client.post(f'{base_url}/auth/register/tenant', json=t_schema.model_dump(mode='json'))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Invite could not be found" in response.json()['detail']