"""
Pytest fixtures for the lodge ownership invitation domain.

Provides mock payloads and pre-seeded database fixtures for:
- Active ownership invites
- Cancelled ownership invites
- Consumed ownership invites
- Expired ownership invites
"""
from datetime import datetime, timedelta, timezone
import pytest

from app.core.enums import OwnershipInviteStatus
from app.crud.ownership_invite import crud_ownership_invite
from app.models.ownership_invite import OwnershipInvite
from app.services import ownership_invite_service
from app.schemas.ownership_invite import OwnershipInviteCreate


@pytest.fixture
def ownership_invite_payload_factory(operator_pilot_lodge, landlord_user):
    """
    Factory fixture to generate ownership invite request payloads with custom overrides.
    """
    def _create(**kwargs):
        payload = {
            "lodge_id": operator_pilot_lodge.id,
            "target_phone_no": landlord_user.phone_no
        }
        payload.update(kwargs)
        return payload
    return _create


@pytest.fixture
def mock_ownership_invite_payload(ownership_invite_payload_factory):
    """
    Returns a default valid request payload for creating an ownership invite.
    """
    return ownership_invite_payload_factory()



@pytest.fixture
def pilot_ownership_invite(test_db, operator_user, operator_pilot_lodge, landlord_user) -> OwnershipInvite:
    """
    Creates an active, phone-locked ownership invite in the database.
    """
    invite_in = OwnershipInviteCreate(
        lodge_id=operator_pilot_lodge.id,
        target_phone_no=landlord_user.phone_no
    )
    return ownership_invite_service.create_ownership_invite(
        db=test_db,
        invite_in=invite_in,
        current_user=operator_user
    )


@pytest.fixture
def cancelled_ownership_invite(test_db, pilot_ownership_invite, operator_user) -> OwnershipInvite:
    """
    Provides an ownership invite that has been cancelled by its creator.
    """
    return ownership_invite_service.cancel_ownership_invite(
        db=test_db,
        invite_id=pilot_ownership_invite.id,
        current_user=operator_user
    )


@pytest.fixture
def consumed_ownership_invite(test_db, pilot_ownership_invite, landlord_user) -> OwnershipInvite:
    """
    Provides an ownership invite that has already been claimed by a landlord.
    """
    ownership_invite_service.claim_ownership_invite(
        db=test_db,
        invite_id=pilot_ownership_invite.id,
        current_user=landlord_user
    )
    return crud_ownership_invite.get_by_id(test_db, invite_id=pilot_ownership_invite.id)


@pytest.fixture
def expired_ownership_invite(test_db, pilot_ownership_invite) -> OwnershipInvite:
    """
    Provides an ownership invite whose expires_at timestamp is in the past.
    """
    pilot_ownership_invite.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    test_db.commit()
    test_db.refresh(pilot_ownership_invite)
    return pilot_ownership_invite
