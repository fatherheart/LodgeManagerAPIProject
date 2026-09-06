"""
Pytest fixtures for the lodge operator invitation domain.

Provides mock payloads and pre-seeded database fixtures for:
- Active operator invites
- Cancelled operator invites
- Accepted operator invites
- Expired operator invites
"""
from datetime import datetime, timedelta, timezone
import pytest

from app.models.operator_invite import OperatorInvite
from app.services import operator_invite_service
from app.schemas.operator_invite import OperatorInviteCreate
from app.crud.crud_operator_invite import crud_operator_invite


@pytest.fixture
def operator_invite_payload_factory(landlord_claimed_lodge, operator_user):
    """
    Factory fixture to generate operator invite request payloads with custom overrides.
    """
    def _create(**kwargs):
        payload = {
            "lodge_id": landlord_claimed_lodge.id,
            "target_phone_no": operator_user.phone_no
        }
        payload.update(kwargs)
        return payload
    return _create


@pytest.fixture
def mock_operator_invite_payload(operator_invite_payload_factory):
    """
    Returns a default valid request payload for creating an operator invite.
    """
    return operator_invite_payload_factory()


@pytest.fixture
def pilot_operator_invite(test_db, landlord_user, landlord_claimed_lodge, operator_user) -> OperatorInvite:
    """
    Creates an active, phone-locked operator invite in the database.
    """
    invite_in = OperatorInviteCreate(
        lodge_id=landlord_claimed_lodge.id,
        target_phone_no=operator_user.phone_no
    )
    return operator_invite_service.create_operator_invite(
        db=test_db,
        invite_in=invite_in,
        current_user=landlord_user
    )


@pytest.fixture
def cancelled_operator_invite(test_db, pilot_operator_invite, landlord_user) -> OperatorInvite:
    """
    Provides an operator invite that has been cancelled by the landlord.
    """
    return operator_invite_service.cancel_operator_invite(
        db=test_db,
        invite_id=pilot_operator_invite.id,
        current_user=landlord_user
    )


@pytest.fixture
def accepted_operator_invite(test_db, pilot_operator_invite, operator_user) -> OperatorInvite:
    """
    Provides an operator invite that has already been accepted.
    """
    return operator_invite_service.accept_operator_invite(
        db=test_db,
        invite_id=pilot_operator_invite.id,
        current_user=operator_user
    )


@pytest.fixture
def expired_operator_invite(test_db, pilot_operator_invite) -> OperatorInvite:
    """
    Provides an operator invite whose expires_at timestamp is in the past.
    """
    pilot_operator_invite.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    test_db.commit()
    test_db.refresh(pilot_operator_invite)
    return pilot_operator_invite
