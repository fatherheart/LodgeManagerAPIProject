"""
Integration tests for the lodge ownership invitation domain.

Covers:
1. Ownership Invite Creation & Deduplication
2. Public Ownership Invite Preview
3. Operator Ownership Invite Cancellation
4. Landlord Ownership Claim & Invariants
"""
import uuid
from fastapi import status

from app.core.enums import OwnershipInviteStatus
from test.conftest import base_url

invites_url = f"{base_url}/invites/ownership"


# =========================================================================
# 1. OWNERSHIP INVITE CREATION & DEDUPLICATION
# =========================================================================

def test_operator_create_ownership_invite_returns_201(
    authenticated_operator_client, mock_ownership_invite_payload
):
    """
    Operator creates an ownership invite for an unclaimed pilot lodge.
    """
    response = authenticated_operator_client.post(invites_url, json=mock_ownership_invite_payload)
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data["lodge_id"] == mock_ownership_invite_payload["lodge_id"]
    assert data["target_phone_no"] == mock_ownership_invite_payload["target_phone_no"]
    assert data["status"] == OwnershipInviteStatus.ACTIVE.value
    assert data["claimed_by_user_id"] is None
    assert "id" in data


def test_operator_create_ownership_invite_returns_existing_active_invite_on_duplicate_call(
    authenticated_operator_client, mock_ownership_invite_payload
):
    """
    Calling create ownership invite twice returns the existing active invite without creating a duplicate.
    """
    response1 = authenticated_operator_client.post(invites_url, json=mock_ownership_invite_payload)
    response2 = authenticated_operator_client.post(invites_url, json=mock_ownership_invite_payload)

    assert response1.status_code == status.HTTP_201_CREATED
    assert response2.status_code == status.HTTP_201_CREATED
    assert response1.json()["id"] == response2.json()["id"]


def test_create_ownership_invite_claimed_lodge_fails_400(
    authenticated_operator_client, hired_caretaker_claimed_lodge, ownership_invite_payload_factory
):
    """
    Cannot generate an ownership invite for a lodge that already has a landlord owner.
    """
    payload = ownership_invite_payload_factory(lodge_id=hired_caretaker_claimed_lodge.id)
    response = authenticated_operator_client.post(invites_url, json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been claimed" in response.json()["detail"]


def test_unassigned_operator_create_ownership_invite_fails_404(
    authenticated_operator_client, other_landlord_lodge, ownership_invite_payload_factory
):
    """
    An unassigned operator cannot generate an ownership invite for a lodge.
    """
    payload = ownership_invite_payload_factory(lodge_id=other_landlord_lodge.id)
    response = authenticated_operator_client.post(invites_url, json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_tenant_create_ownership_invite_fails_403(
    authenticated_tenant_client, mock_ownership_invite_payload
):
    """
    Tenants cannot access ownership invite creation.
    """
    response = authenticated_tenant_client.post(invites_url, json=mock_ownership_invite_payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# =========================================================================
# 2. PUBLIC OWNERSHIP INVITE PREVIEW
# =========================================================================

def test_public_preview_ownership_invite_returns_200(client, pilot_ownership_invite):
    """
    Unauthenticated public client previews an active ownership invite by UUID.
    """
    response = client.get(f"{invites_url}/{pilot_ownership_invite.id}")
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["invite_id"] == str(pilot_ownership_invite.id)
    assert data["lodge_name"] == pilot_ownership_invite.lodge.name
    assert data["target_phone_no"] == pilot_ownership_invite.target_phone_no
    assert data["status"] == OwnershipInviteStatus.ACTIVE.value
    assert data["claimed_by_user_id"] is None


def test_public_preview_non_existent_ownership_invite_returns_404(client):
    """
    Previewing a non-existent ownership invite UUID returns 404.
    """
    random_id = uuid.uuid4()
    response = client.get(f"{invites_url}/{random_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# =========================================================================
# 3. OPERATOR OWNERSHIP INVITE CANCELLATION
# =========================================================================

def test_operator_cancel_ownership_invite_returns_200(
    authenticated_operator_client, pilot_ownership_invite, ownership_invite_payload_factory
):
    """
    Operator cancels an active invite. Status flips to Cancelled,
    unblocking immediate re-issue with a corrected phone number.
    """
    cancel_resp = authenticated_operator_client.delete(f"{invites_url}/{pilot_ownership_invite.id}")
    assert cancel_resp.status_code == status.HTTP_200_OK
    assert cancel_resp.json()["status"] == OwnershipInviteStatus.CANCELLED.value

    # Immediate re-issue with factory-generated payload succeeds
    new_payload = ownership_invite_payload_factory(target_phone_no="08099998877")
    new_create = authenticated_operator_client.post(invites_url, json=new_payload)
    assert new_create.status_code == status.HTTP_201_CREATED
    assert new_create.json()["id"] != str(pilot_ownership_invite.id)
    assert new_create.json()["target_phone_no"] == "08099998877"


def test_non_creator_operator_cancel_ownership_invite_fails_403(
    auth_client_factory, other_operator_user, pilot_ownership_invite
):
    """
    An operator who did not create the ownership invite cannot cancel it.
    """
    other_client = auth_client_factory(user_id=other_operator_user.id)
    cancel_resp = other_client.delete(f"{invites_url}/{pilot_ownership_invite.id}")

    assert cancel_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "Only the operator who created" in cancel_resp.json()["detail"]


def test_cancel_already_cancelled_ownership_invite_fails_400(
    authenticated_operator_client, cancelled_ownership_invite
):
    """
    Cancelling an already cancelled ownership invite returns 400.
    """
    response = authenticated_operator_client.delete(f"{invites_url}/{cancelled_ownership_invite.id}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been cancelled" in response.json()["detail"]


# =========================================================================
# 4. LANDLORD OWNERSHIP CLAIM & INVARIANTS
# =========================================================================

def test_landlord_claim_ownership_invite_returns_200(
    authenticated_landlord_client, pilot_ownership_invite, landlord_user
):
    """
    Landlord with matching phone claims ownership:
    - Lodge landlord_id is updated atomically
    - Response returns claimed lodge
    - Invite status becomes Consumed
    """
    claim_resp = authenticated_landlord_client.post(f"{invites_url}/{pilot_ownership_invite.id}/claim")
    data = claim_resp.json()

    assert claim_resp.status_code == status.HTTP_200_OK
    assert data["id"] == pilot_ownership_invite.lodge_id
    assert data["landlord_id"] == landlord_user.id

    # Verify public preview reflects Consumed
    preview_resp = authenticated_landlord_client.get(f"{invites_url}/{pilot_ownership_invite.id}")
    assert preview_resp.json()["status"] == OwnershipInviteStatus.CONSUMED.value
    assert preview_resp.json()["claimed_by_user_id"] == landlord_user.id


def test_claim_ownership_invite_phone_mismatch_fails_400(
    auth_client_factory, other_landlord_user, pilot_ownership_invite
):
    """
    Landlord whose phone number does not match target_phone_no cannot claim.
    """
    other_client = auth_client_factory(user_id=other_landlord_user.id)
    response = other_client.post(f"{invites_url}/{pilot_ownership_invite.id}/claim")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "tied to a different phone number" in response.json()["detail"]


def test_claim_already_consumed_ownership_invite_fails_400(
    authenticated_landlord_client, consumed_ownership_invite
):
    """
    Claiming an already consumed ownership invite returns 400.
    """
    response = authenticated_landlord_client.post(f"{invites_url}/{consumed_ownership_invite.id}/claim")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been claimed" in response.json()["detail"]


def test_claim_cancelled_ownership_invite_fails_400(
    authenticated_landlord_client, cancelled_ownership_invite
):
    """
    Claiming a cancelled ownership invite returns 400.
    """
    response = authenticated_landlord_client.post(f"{invites_url}/{cancelled_ownership_invite.id}/claim")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already been cancelled" in response.json()["detail"]


def test_claim_expired_ownership_invite_fails_400(
    authenticated_landlord_client, expired_ownership_invite
):
    """
    Claiming an expired ownership invite returns 400.
    """
    response = authenticated_landlord_client.post(f"{invites_url}/{expired_ownership_invite.id}/claim")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "has expired" in response.json()["detail"]


def test_tenant_claim_ownership_invite_fails_403(
    authenticated_tenant_client, pilot_ownership_invite
):
    """
    Tenants cannot access the ownership claim endpoint.
    """
    response = authenticated_tenant_client.post(f"{invites_url}/{pilot_ownership_invite.id}/claim")
    assert response.status_code == status.HTTP_403_FORBIDDEN
