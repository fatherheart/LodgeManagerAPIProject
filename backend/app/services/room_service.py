"""
Module providing room-related business logic.

This module contains services for managing rooms, requiring active operator assignment.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.core import constants
from app.core.enums import RoomStatus
from app.models.room import Room
from app.models.user import User
from app.schemas import room as schema_room
from app.schemas.room import RoomResponse, RoomCreate, BulkRoomUpdate, PendingApplicantSummary
from app.crud.room import crud_room
from app.services import lodge_service
from app.core.exceptions import (
    RoomAlreadyExistError,
    RoomNotFoundError,
    RoomIsOccupiedError,
    NotUpdatableOptionError,
    BaseNotAllowedError, LodgeNotFoundError
)


def create_room_for_lodge(
    db: Session,
    room_in: schema_room.RoomCreate,
    current_user: User
) -> Room:
    """
    Create a new room in a specific lodge for an authorized lodge operator.
    """
    lodge = lodge_service.require_lodge_operator(
        db=db, lodge_id=room_in.lodge_id, user_id=current_user.id
    )

    room = crud_room.get_room_by_lodge_and_number(db=db, room_no=room_in.room_no, lodge_id=lodge.id)
    if room:
        raise RoomAlreadyExistError(room_in.room_no)

    return crud_room.create(db=db, obj_in=room_in)


def get_lodge_rooms(
    db: Session,
    lodge_id: int,
    current_user: User,
    skip: Optional[int] = None,
    limit: Optional[int] = None
) -> List[Room]:
    """
    Get all rooms for an authorized lodge operator.
    """
    lodge_service.require_lodge_operator(
        db=db, lodge_id=lodge_id, user_id=current_user.id
    )
    return crud_room.get_rooms(db, lodge_id=lodge_id, skip=skip, max_limit=limit)


def verify_room_existence(
    db: Session,
    room_id: int,
    current_user: User
) -> Room:
    """
    Verify if a room exists and the caller has active operational access to its lodge.
    """
    options = joinedload(Room.lodge)
    room = crud_room.get(db, room_id, options)

    if not room or not room.lodge:
        raise RoomNotFoundError()

    if not lodge_service.user_can_access_room_lodge(room, current_user=current_user, db=db):
        raise RoomNotFoundError(room_no=room.room_no)

    return room


def get_room_details(
    db: Session,
    room_id: int,
    current_user: User
) -> RoomResponse:
    """
    Get the details of a specific room, including its onboarding states.
    """
    row = crud_room.get_room_with_onboarding_state(db, room_id=room_id)
    if not row:
        raise RoomNotFoundError()

    room_obj = row.Room
    lodge_service.require_lodge_operator(
        db=db, lodge_id=room_obj.lodge_id, user_id=current_user.id
    )

    pending_dto = None
    if row.tenant_id:
        pending_dto = PendingApplicantSummary(
            tenant_id=row.tenant_id,
            first_name=row.first_name,
            last_name=row.last_name,
            phone_no=row.phone_no
        )

    room_dto = RoomResponse.model_validate(room_obj)
    room_dto.has_active_invite = row.has_active_invite
    room_dto.pending_applicant = pending_dto

    return room_dto


def update_room_details(
    db: Session,
    room_id: int,
    update_data: schema_room.RoomUpdate,
    current_user: User
) -> Room:
    """
    Update the details of a specific room.
    Allowed for VACANT and MAINTENANCE rooms. Blocked for OCCUPIED rooms.
    """
    room = verify_room_existence(db=db, room_id=room_id, current_user=current_user)

    if room.is_occupied:
        raise RoomIsOccupiedError(occupied_room_no=room.room_no)

    if update_data.status and update_data.status not in constants.UPDATABLE_ROOM_STATUSES:
        raise NotUpdatableOptionError(
            allowed_options=constants.UPDATABLE_ROOM_STATUSES,
            update_status=update_data.status
        )

    if update_data.base_rent_price is not None and room.lodge.is_claimed:
        if not room.lodge.is_owned_by(current_user.id):
            raise BaseNotAllowedError(entity_name='lodge owners')

    return crud_room.update(db=db, db_obj=room, update_data=update_data)


def bulk_update_base_rent(
    db: Session,
    lodge_id: int,
    update_data: BulkRoomUpdate,
    current_user: User
) -> List[Room]:
    """
    Bulk update base rent for specified rooms in an authorized lodge.
    """
    lodge = lodge_service.require_lodge_operator(
        db=db, lodge_id=lodge_id, user_id=current_user.id
    )

    if lodge.is_claimed and not lodge.is_owned_by(current_user.id):
        raise BaseNotAllowedError(entity_name='lodge owners')


    to_update_rooms = crud_room.get_updatable_rooms(
        db,
        room_ids=update_data.room_ids,
        lodge_id=lodge_id
    )

    if not to_update_rooms:
        room_nos_str = ', '.join(str(n) for n in update_data.room_ids)
        raise RoomNotFoundError(room_nos_str)

    if len(to_update_rooms) != len(update_data.room_ids):
        raise RoomNotFoundError(detail='One or more rooms')

    for room in to_update_rooms:
        if room.is_occupied:
            raise RoomIsOccupiedError(occupied_room_no=room.room_no)
        room.base_rent_price = update_data.base_rent

    db.commit()
    return to_update_rooms
