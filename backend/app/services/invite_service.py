"""
Module providing tenant room invitation logic.

Supports idempotent invite generation by both Landlords and Operators.
"""
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.enums import RoomStatus
from app.core.exceptions import InviteNotFoundError, RoomNotAvailableError
from app.crud.invite import crud_invite
from app.models.invitation import Invite
from app.models.user import User
from app.schemas import invitation as schema_invite
from app.services import room_service


def invite_tenant(
    db: Session,
    invite_in: schema_invite.InviteCreate,
    current_user: User
) -> Invite:
    """
    Generate or retrieve an active invitation token for a vacant room.
    Idempotent: if an active unexpired invite already exists, returns it.
    """
    room = room_service.verify_room_existence(db, room_id=invite_in.room_id, current_user=current_user)

    if room.computed_status != RoomStatus.VACANT:
        raise RoomNotAvailableError(room_no=room.room_no, room_status=room.computed_status.value)

    # Idempotent behavior: return active invite if one is already pending
    active_invite = crud_invite.get_active_invite_for_room(db, room_id=room.id)
    if active_invite:
        return active_invite

    return crud_invite.add_invite_record(db, invite_in=invite_in)


def fetch_invite_record(db: Session, invite_id: UUID) -> Invite:
    """
    Fetch public invite details by UUID token.
    """
    invite_record = crud_invite.get_invite_record_by_id(db, invite_id=invite_id)

    if not invite_record:
        raise InviteNotFoundError(invite_id=invite_id)

    return invite_record