"""
Module providing business logic for lodge operator invitations.

Supports:
- Generating or returning existing active phone-locked operator invitations by lodge owners
- Public inspection of an operator invite and its computed status
- Cancelling an invite by its creator
- Authenticated acceptance of an operator invite with phone verification and atomic assignment
- Revocation of an active operator assignment by the lodge owner
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.enums import OperatorInviteStatus, OperatorStatus
from app.core.exceptions import (
    OperatorInviteNotFoundError,
    PhoneMismatchError,
    InviteExpiredError,
    InviteAlreadyConsumedError,
    InviteAlreadyCancelledError,
    NotInviteCreatorError,
    OperatorAlreadyAssignedError,
    OperatorNotAssignedError,
)
from app.crud.crud_operator_invite import crud_operator_invite
from app.crud.crud_lodge_operator import crud_lodge_operator
from app.crud.user import crud_user
from app.models.operator_invite import OperatorInvite
from app.models.lodge_operator import LodgeOperator
from app.models.user import User
from app.schemas.operator_invite import OperatorInviteCreate
from app.services import lodge_service


def verify_operator_invite_is_actionable(invite: OperatorInvite) -> None:
    """
    Ensure an operator invitation is in a valid actionable state.
    Raises domain exceptions if already accepted, cancelled, or expired.
    """
    status = invite.computed_status
    if status == OperatorInviteStatus.ACCEPTED:
        raise InviteAlreadyConsumedError()
    if status == OperatorInviteStatus.CANCELLED:
        raise InviteAlreadyCancelledError()
    if status == OperatorInviteStatus.EXPIRED:
        raise InviteExpiredError()


def create_operator_invite(
    db: Session,
    invite_in: OperatorInviteCreate,
    current_user: User
) -> OperatorInvite:
    """
    Generate a new operator assignment invite or return existing active one (idempotent).
    Only the legal owner of the lodge can invite an operator.
    """
    # 1. Enforce lodge owner gate
    lodge = lodge_service.require_lodge_owner(db, lodge_id=invite_in.lodge_id, user_id=current_user.id)

    # 2. Invariant: Target phone number must not already be an active operator for this lodge
    target_user = crud_user.get_user_by_phone(db, phone=invite_in.target_phone_no)
    if target_user:
        active_assignment = crud_lodge_operator.get_active_assignment(
            db, lodge_id=lodge.id, operator_id=target_user.id
        )
        if active_assignment:
            raise OperatorAlreadyAssignedError(operator_id=target_user.id)

    # 3. Idempotent check: Return active pending invite if one exists
    existing = crud_operator_invite.get_active_invite_for_phone_and_lodge(
        db, lodge_id=lodge.id, target_phone_no=invite_in.target_phone_no
    )
    if existing:
        return existing

    # 4. Create new 7-day phone-locked invite
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    return crud_operator_invite.create_invite(
        db=db,
        lodge_id=lodge.id,
        created_by_user_id=current_user.id,
        target_phone_no=invite_in.target_phone_no,
        expires_at=expires_at
    )



def fetch_operator_invite(db: Session, invite_id: UUID) -> OperatorInvite:
    """
    Public lookup for an operator invite by UUID token.
    Raises OperatorInviteNotFoundError if the invite does not exist.
    """
    invite = crud_operator_invite.get_by_id(db, invite_id=invite_id)
    if not invite:
        raise OperatorInviteNotFoundError(invite_id=invite_id)
    return invite


def cancel_operator_invite(
    db: Session,
    invite_id: UUID,
    current_user: User
) -> OperatorInvite:
    """
    Landlord cancels a pending operator invite.
    Only the creator of the invite can cancel it.
    """
    invite = crud_operator_invite.get_by_id(db, invite_id=invite_id)
    if not invite:
        raise OperatorInviteNotFoundError(invite_id=invite_id)

    if invite.created_by_user_id != current_user.id:
        raise NotInviteCreatorError()

    verify_operator_invite_is_actionable(invite)

    return crud_operator_invite.cancel(db, invite=invite)


def accept_operator_invite(
    db: Session,
    invite_id: UUID,
    current_user: User
) -> OperatorInvite:
    """
    Operator accepts assignment to manage a lodge.
    Enforces:
    - Invite must be ACTIVE
    - Phone number of current_user must match target_phone_no
    - User must not already be actively assigned
    Atomically marks invite ACCEPTED and assigns operator in LodgeOperator.
    """
    invite = crud_operator_invite.get_by_id(db, invite_id=invite_id)
    if not invite:
        raise OperatorInviteNotFoundError(invite_id=invite_id)

    # 1. State check on invite
    verify_operator_invite_is_actionable(invite)

    # 2. Invariant: User not already assigned
    active_assignment = crud_lodge_operator.get_active_assignment(
        db, lodge_id=invite.lodge_id, operator_id=current_user.id
    )
    if active_assignment:
        raise OperatorAlreadyAssignedError(operator_id=current_user.id)

    # 3. Security Guard: Phone number verification
    if current_user.phone_no != invite.target_phone_no:
        raise PhoneMismatchError(
            target_phone=invite.target_phone_no,
            user_phone=current_user.phone_no
        )

    # 4. Handle operator assignment at the domain/service layer
    existing_assignment = crud_lodge_operator.get_assignment_by_lodge_and_operator(
        db, lodge_id=invite.lodge_id, operator_id=current_user.id
    )
    if existing_assignment:
        existing_assignment.status = OperatorStatus.ASSIGNED
        existing_assignment.revoked_at = None
    else:
        new_assignment = LodgeOperator(
            operator_id=current_user.id,
            lodge_id=invite.lodge_id,
            status=OperatorStatus.ASSIGNED
        )
        invite.lodge.operators.append(new_assignment)

    # 5. Delegate pure atomic persistence to CRUD
    return crud_operator_invite.accept(
        db=db,
        invite=invite,
        accepted_by_user_id=current_user.id
    )


def revoke_operator(
    db: Session,
    lodge_id: int,
    operator_id: int,
    current_user: User
) -> LodgeOperator:
    """
    Lodge owner revokes an active operator assignment.
    Only the lodge owner can revoke an operator.
    """
    # 1. Enforce lodge owner gate
    lodge_service.require_lodge_owner(db, lodge_id=lodge_id, user_id=current_user.id)

    # 2. Check active assignment
    assignment = crud_lodge_operator.get_active_assignment(
        db, lodge_id=lodge_id, operator_id=operator_id
    )
    if not assignment:
        raise OperatorNotAssignedError(operator_id=operator_id)

    # 3. Mark as revoked
    return crud_lodge_operator.mark_as_revoked(db, assignment=assignment)
