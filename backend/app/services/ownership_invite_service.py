"""
Module providing business logic for lodge ownership invitations.

Supports:
- Generating or returning existing active phone-locked ownership invitations (idempotent)
- Public inspection of an invitation and its computed status
- Cancelling an invitation by its creator
- Authenticated claiming of ownership by a landlord with phone verification and atomic transfer
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.enums import OwnershipInviteStatus, UserRole
from app.core.exceptions import (
    OwnershipInviteNotFoundError,
    PhoneMismatchError,
    InviteExpiredError,
    InviteAlreadyConsumedError,
    InviteAlreadyCancelledError,
    LodgeAlreadyClaimedError,
    NotInviteCreatorError,
)
from app.crud.ownership_invite import crud_ownership_invite
from app.models.ownership_invite import OwnershipInvite
from app.models.lodge import Lodge
from app.models.user import User
from app.schemas.ownership_invite import OwnershipInviteCreate
from app.services import lodge_service


def create_ownership_invite(
    db: Session,
    invite_in: OwnershipInviteCreate,
    current_user: User
) -> OwnershipInvite:
    """
    Generate a new ownership claim invitation or return the existing active one (idempotent).
    Only an actively assigned operator of an unclaimed lodge can generate this invite.
    """
    # 1. Enforce active operator assignment gate
    lodge = lodge_service.require_lodge_operator(db, lodge_id=invite_in.lodge_id, user_id=current_user.id)

    # 2. Invariant: Lodge must be unclaimed
    if lodge.is_claimed:
        raise LodgeAlreadyClaimedError()

    # 3. Idempotent check: If an active invite already exists, return it
    existing_invite = crud_ownership_invite.get_active_invite_for_lodge(db, lodge_id=lodge.id)
    if existing_invite:
        return existing_invite

    # 4. Create new 7-day phone-locked invite
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    return crud_ownership_invite.create(
        db=db,
        lodge_id=lodge.id,
        created_by_user_id=current_user.id,
        target_phone_no=invite_in.target_phone_no,
        expires_at=expires_at
    )


def fetch_ownership_invite(db: Session, invite_id: UUID) -> OwnershipInvite:
    """
    Public lookup for an ownership invite by UUID token.
    Raises OwnershipInviteNotFoundError if the invite does not exist.
    """
    invite = crud_ownership_invite.get_by_id(db, invite_id=invite_id)
    if not invite:
        raise OwnershipInviteNotFoundError(invite_id=invite_id)
    return invite


def verify_invite_is_actionable(invite: OwnershipInvite) -> None:

    """
    Ensure an invitation is in a valid actionable state.
    Raises domain exceptions if the invite is already consumed, cancelled, or expired.
    """
    invite_status = invite.computed_status
    if invite_status == OwnershipInviteStatus.CONSUMED:
        raise InviteAlreadyConsumedError()
    if invite_status == OwnershipInviteStatus.CANCELLED:
        raise InviteAlreadyCancelledError()
    if invite_status == OwnershipInviteStatus.EXPIRED:
        raise InviteExpiredError()


def cancel_ownership_invite(
    db: Session,
    invite_id: UUID,
    current_user: User
) -> OwnershipInvite:
    """
    Operator cancels a pending ownership invite.
    Only the operator who created the invite can cancel it.
    """
    invite = crud_ownership_invite.get_by_id(db, invite_id=invite_id)
    if not invite:
        raise OwnershipInviteNotFoundError(invite_id=invite_id)

    # Only creator can cancel
    if invite.created_by_user_id != current_user.id:
        raise NotInviteCreatorError()

    verify_invite_is_actionable(invite)

    return crud_ownership_invite.cancel(db, invite=invite)


def claim_ownership_invite(
    db: Session,
    invite_id: UUID,
    current_user: User
) -> Lodge:
    """
    Landlord claims legal ownership of a lodge via an active invite.
    Enforces:
    - User must be a landlord
    - Invite must be ACTIVE (not EXPIRED, CANCELLED, or CONSUMED)
    - Phone number of current_user must match invite target_phone_no
    - Lodge must still be unclaimed
    Delegates atomic persistence to CRUD and returns the claimed lodge.
    """
    invite = crud_ownership_invite.get_by_id(db, invite_id=invite_id)
    if not invite:
        raise OwnershipInviteNotFoundError(invite_id=invite_id)

    # 1. State check on invite
    verify_invite_is_actionable(invite)

    # 2. Invariant: Lodge must still be unclaimed
    if invite.lodge.is_claimed:
        raise LodgeAlreadyClaimedError()

    # 3. Security Guard: Phone number verification
    if current_user.phone_no != invite.target_phone_no:
        raise PhoneMismatchError(
            target_phone=invite.target_phone_no,
            user_phone=current_user.phone_no
        )

    # 4. Atomic transfer delegated completely to CRUD
    return crud_ownership_invite.consume(
        db=db,
        invite=invite,
        claimed_by_user_id=current_user.id
    )

