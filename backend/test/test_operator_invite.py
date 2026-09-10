"""
Integration tests for the lodge operator invitation and revocation domain.

Covers:
1. Operator Invite Creation & Deduplication
2. Public Operator Invite Preview
3. Landlord Operator Invite Cancellation
4. Operator Acceptance & Invariants
5. Landlord Operator Revocation
"""
import uuid
from fastapi import status

from app.core.enums import OperatorInviteStatus, OperatorStatus
from test.conftest import base_url

invites_url = f"{base_url}/invites/operator"
lodges_url = f"{base_url}/lodges"


# =========================================================================
# 1. OPERATOR INVITE CREATION & DEDUPLICATION
# =========================================================================

def test_landlord_create_operator_invite_returns_201(
    authenticated_landlord_client, mock_operator_invite_payload
):
    """
    Landlord creates an operator invite for an owned lodge.
    """
    response = authenticated_landlord_client.post(invites_url, json=mock_operator_invite_payload)
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data["lodge_id"] == mock_operator_invite_payload["lodge_id"]
    assert data["target_phone_no"] == mock_operator_invite_payload["target_phone_no"]
    assert data["status"] == OperatorInviteStatus.ACTIVE.value
    assert data["accepted_by_user_id"] is None
    assert "id" in data


def test_landlord_create_operator_invite_returns_existing_active_invite_on_duplicate_call(
    authenticated_landlord_client, mock_operator_invite_payload
):
    """
    Calling create operator invite twice returns the exact same active invite without creating a duplicate.
    """
    response1 = authenticated_landlord_client.post(invites_url, json=mock_operator_invite_payload)
    response2 = authenticated_landlord_client.post(invites_url, json=mock_operator_invite_payload)

    assert response1.status_code == status.HTTP_201_CREATED
    assert response2.status_code == status.HTTP_201_CREATED
    assert response1.json()["id"] == response2.json()["id"]
    assert response1.json()["target_phone_no"] == response2.json()["target_phone_no"]


def test_create_operator_invite_for_already_assigned_operator_fails_400(
    authenticated_landlord_client, hired_caretaker_claimed_lodge, operator_user
):
    """
    Cannot generate an operator invite for someone who is already actively assigned to this lodge.
    """
    payload = {
        "lodge_id": hired_caretaker_claimed_lodge.id,
        "target_phone_no": operator_user.phone_no
    }
    response = authenticated_landlord_client.post(invites_url, json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already actively assigned" in response.json()["detail"]


def test_non_owner_create_operator_invite_fails_404(
    auth_client_factory, other_landlord_user, landlord_claimed_lodge, operator_user
):
    """
    A landlord who does not own the lodge cannot generate operator invites for it (returns 404).
    """
    other_client = auth_client_factory(user_id=other_landlord_user.id)
    payload = {
        "lodge_id": landlord_claimed_lodge.id,
        "target_phone_no": operator_user.phone_no
    }
    response = other_client.post(invites_url, json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Lodge could not be found" in response.json()["detail"]


def test_tenant_create_operator_invite_fails_403(
    authenticated_tenant_client, mock_operator_invite_payload
):
    """
    Tenants cannot create operator invites.
    """
    response = authenticated_tenant_client.post(invites_url, json=mock_operator_invite_payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Only landlords are allowed" in response.json()["detail"]


# =========================================================================
# 2. PUBLIC OPERATOR INVITE PREVIEW
# =========================================================================

def test_public_preview_operator_invite_returns_200(client, pilot_operator_invite):
    """
    Unauthenticated public client previews an active operator invite by UUID.
    """
    response = client.get(f"{invites_url}/{pilot_operator_invite.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["invite_id"] == str(pilot_operator_invite.id)
    assert data["lodge_name"] == pilot_operator_invite.lodge.name
    assert data["target_phone_no"] == pilot_operator_invite.target_phone_no
    assert data["status"] == OperatorInviteStatus.ACTIVE.value


def test_public_preview_non_existent_operator_invite_returns_404(client):
    """
    Previewing a non-existent operator invite UUID returns 404 with exact detail.
    """
    random_id = uuid.uuid4()
    response = client.get(f"{invites_url}/{random_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Operator Invitation could not be found" in response.json()["detail"]


# =========================================================================
# 3. LANDLORD OPERATOR INVITE CANCELLATION
# =========================================================================

def test_landlord_cancel_operator_invite_returns_200(
    authenticated_landlord_client, pilot_operator_invite, operator_invite_payload_factory
):
    """
    Landlord cancels an active operator invite. Status becomes Cancelled,
    unblocking immediate re-issue.
    """
    cancel_resp = authenticated_landlord_client.delete(f"{invites_url}/{pilot_operator_invite.id}")
    assert cancel_resp.status_code == status.HTTP_200_OK
    assert cancel_resp.json()["status"] == OperatorInviteStatus.CANCELLED.value

    # Immediate re-issue succeeds
    new_payload = operator_invite_payload_factory(target_phone_no="08099887766")
    new_resp = authenticated_landlord_client.post(invites_url, json=new_payload)
    assert new_resp.status_code == status.HTTP_201_CREATED
    assert new_resp.json()["id"] != str(pilot_operator_invite.id)


def test_non_creator_cancel_operator_invite_fails_403(
    auth_client_factory, other_landlord_user, pilot_operator_invite
):
    """
    A landlord who did not create the invite cannot cancel it.
    """
    other_client = auth_client_factory(user_id=other_landlord_user.id)
    cancel_resp = other_client.delete(f"{invites_url}/{pilot_operator_invite.id}")
    assert cancel_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "Only the operator who created" in cancel_resp.json()["detail"]


def test_cancel_already_cancelled_operator_invite_fails_400(
    authenticated_landlord_client, cancelled_operator_invite
):
    """
    Cancelling an already cancelled invite returns 400.
    """
    response = authenticated_landlord_client.delete(f"{invites_url}/{cancelled_operator_invite.id}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been cancelled" in response.json()["detail"]


# =========================================================================
# 4. OPERATOR ACCEPTANCE & INVARIANTS
# =========================================================================

def test_operator_accept_operator_invite_returns_200(
    authenticated_operator_client, pilot_operator_invite, operator_user
):
    """
    Operator with matching phone accepts management:
    - Status becomes Accepted
    - Operator is assigned to the lodge
    - Operator can immediately access the lodge endpoint
    """
    accept_resp = authenticated_operator_client.post(f"{invites_url}/{pilot_operator_invite.id}/accept")
    data = accept_resp.json()

    assert accept_resp.status_code == status.HTTP_200_OK
    assert data["status"] == OperatorInviteStatus.ACCEPTED.value
    assert data["accepted_by_user_id"] == operator_user.id

    # Operational verify: Operator can immediately access and manage the lodge
    lodge_resp = authenticated_operator_client.get(f"{lodges_url}/{pilot_operator_invite.lodge_id}")
    assert lodge_resp.status_code == status.HTTP_200_OK
    assert lodge_resp.json()["id"] == pilot_operator_invite.lodge_id

    # Verify public preview reflects Accepted
    preview_resp = authenticated_operator_client.get(f"{invites_url}/{pilot_operator_invite.id}")
    assert preview_resp.json()["status"] == OperatorInviteStatus.ACCEPTED.value


def test_accept_operator_invite_phone_mismatch_fails_400(
    auth_client_factory, other_operator_user, pilot_operator_invite
):
    """
    Operator whose phone number does not match target_phone_no cannot accept.
    """
    other_client = auth_client_factory(user_id=other_operator_user.id)
    response = other_client.post(f"{invites_url}/{pilot_operator_invite.id}/accept")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tied to a different phone number" in response.json()["detail"]


def test_accept_already_accepted_operator_invite_fails_400(
    authenticated_operator_client, accepted_operator_invite
):
    """
    Accepting an already accepted invite returns 400.
    """
    response = authenticated_operator_client.post(f"{invites_url}/{accepted_operator_invite.id}/accept")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been claimed or accepted" in response.json()["detail"]


def test_accept_cancelled_operator_invite_fails_400(
    authenticated_operator_client, cancelled_operator_invite
):
    """
    Accepting a cancelled invite returns 400.
    """
    response = authenticated_operator_client.post(f"{invites_url}/{cancelled_operator_invite.id}/accept")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been cancelled" in response.json()["detail"]


def test_accept_expired_operator_invite_fails_400(
    authenticated_operator_client, expired_operator_invite
):
    """
    Accepting an expired invite returns 400.
    """
    response = authenticated_operator_client.post(f"{invites_url}/{expired_operator_invite.id}/accept")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "has expired" in response.json()["detail"]


def test_tenant_cannot_accept_operator_invite_fails_403(
    authenticated_tenant_client, pilot_operator_invite
):
    """
    Tenants cannot accept operator invites.
    """
    response = authenticated_tenant_client.post(f"{invites_url}/{pilot_operator_invite.id}/accept")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Only operators or landlords are allowed" in response.json()["detail"]


# =========================================================================
# 5. LANDLORD OPERATOR REVOCATION (PATCH /lodges/{lodge_id}/operators/{operator_id})
# =========================================================================

def test_landlord_revoke_operator_returns_200(
    auth_client_factory, landlord_user, hired_caretaker_claimed_lodge, operator_user
):
    """
    Lodge owner revokes an active operator via PATCH /lodges/{id}/operators/{operator_id}:
    - Status flips to REVOKED in response
    - Response contains operator_id and lodge_id
    - Operator is immediately locked out of lodge management endpoints
    """
    landlord_client = auth_client_factory(user_id=landlord_user.id)
    revoke_url = f"{lodges_url}/{hired_caretaker_claimed_lodge.id}/operators/{operator_user.id}"
    response = landlord_client.patch(revoke_url)
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["lodge_id"] == hired_caretaker_claimed_lodge.id
    assert data["operator_id"] == operator_user.id
    assert data["status"] == OperatorStatus.REVOKED.value
    assert data["revoked_at"] is not None

    # Operational lockout check: Operator is instantly forbidden from lodge operations
    operator_client = auth_client_factory(user_id=operator_user.id)
    operator_lodge_resp = operator_client.get(f"{lodges_url}/{hired_caretaker_claimed_lodge.id}")
    assert operator_lodge_resp.status_code == status.HTTP_404_NOT_FOUND


def test_non_owner_revoke_operator_fails_404(
    auth_client_factory, other_landlord_user, hired_caretaker_claimed_lodge, operator_user
):
    """
    A non-owner landlord cannot revoke an operator from another landlord's lodge (returns 404).
    """
    other_client = auth_client_factory(user_id=other_landlord_user.id)
    revoke_url = f"{lodges_url}/{hired_caretaker_claimed_lodge.id}/operators/{operator_user.id}"
    response = other_client.patch(revoke_url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Lodge could not be found" in response.json()["detail"]


def test_revoke_unassigned_operator_fails_400(
    authenticated_landlord_client, landlord_claimed_lodge, operator_user
):
    """
    Attempting to revoke an operator who is not assigned to the lodge returns 400.
    """
    revoke_url = f"{lodges_url}/{landlord_claimed_lodge.id}/operators/{operator_user.id}"
    response = authenticated_landlord_client.patch(revoke_url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not actively assigned" in response.json()["detail"]
