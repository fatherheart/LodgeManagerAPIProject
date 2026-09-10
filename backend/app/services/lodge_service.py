"""
Module providing lodge-related business logic.

This module enforces the 3-layer architecture:
- Identity: User.role
- Assignment: LodgeOperator (require_lodge_operator)
- Permission / Ownership: Legal title in Lodge.landlord_id (require_lodge_owner)
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.core.enums import UserRole, OperatorStatus
from app.models.lodge import Lodge
from app.models.room import Room
from app.models.user import User
from app.models.lodge_operator import LodgeOperator
from app.schemas.lodge import LodgeCreate, LodgeUpdate, RoomGenerator
from app.core.exceptions import (
    LodgeAlreadyExistError,
    LodgeNotFoundError,
    BaseNotAllowedError
)
from app.crud.lodge import crud_lodge
from app.crud.crud_lodge_operator import crud_lodge_operator


def is_landlord(user_role: UserRole) -> bool:
    """Check if a user role is landlord."""
    return user_role == UserRole.LANDLORD


def is_tenant(user_role: UserRole) -> bool:
    """Check if a user role is tenant."""
    return user_role == UserRole.TENANT


def is_operator(user_role: UserRole) -> bool:
    """Check if a user role is operator."""
    return user_role == UserRole.OPERATOR


def is_operator_or_landlord(user_role: UserRole) -> bool:
    """Check if a user role is either operator or landlord."""
    return user_role in (UserRole.OPERATOR, UserRole.LANDLORD)


def _setup_lodge_with_rooms(lodge_in: LodgeCreate,created_by_user_id: int, landlord_id: Optional[int] = None) -> Lodge:
    """
    Pure helper function to instantiate a Lodge entity and populate its room collection.
    If prefix is provided (e.g. 'A'), generates 'A1', 'A2'. If omitted, generates '1', '2'.
    Returns the in-memory Lodge tree ready for commit.
    """
    lodge_dict = lodge_in.model_dump(exclude={'room_generator'})
    new_lodge = Lodge(
        **lodge_dict,
        landlord_id=landlord_id,
        created_by_user_id=created_by_user_id
    )

    room_gen: Optional[RoomGenerator] = lodge_in.room_generator
    if room_gen:
        prefix = room_gen.prefix.strip() if room_gen.prefix else ""
        for i in range(room_gen.start_number, room_gen.end_number + 1):
            room_no = f'{prefix}{i}' if prefix else str(i)
            room_data = Room(
                room_no=room_no,
                base_rent_price=room_gen.default_rent,
                description=room_gen.default_description
            )
            new_lodge.rooms.append(room_data)

    return new_lodge



def create_new_lodge_for_authorized_user(
        db: Session,
        current_user: User,
        lodge_data: LodgeCreate
) -> Lodge:
    """
    Unified lodge creation for both Landlords and Operators.
    - Landlords: Creates a claimed property under their ownership.
    - Operators: Creates an unclaimed pilot property + active LodgeOperator assignment.
    """

    is_landlord_creator = is_landlord(current_user.role)
    if is_landlord_creator:
        existing = crud_lodge.get_by_name_and_landlord(
            db, lodge_name=lodge_data.name, landlord_id=current_user.id
        )
    else:
        existing = crud_lodge.get_by_name_and_creator(
            db, lodge_name=lodge_data.name, creator_id=current_user.id
        )

    if existing:
        raise LodgeAlreadyExistError(name=lodge_data.name)


    new_lodge = _setup_lodge_with_rooms(
        lodge_in=lodge_data,
        landlord_id=current_user.id if is_landlord_creator else None,
        created_by_user_id=current_user.id
    )


    if not is_landlord_creator:
        operator_assignment = LodgeOperator(
            operator_id=current_user.id,
            status=OperatorStatus.ASSIGNED
        )
        new_lodge.operators.append(operator_assignment)

    return crud_lodge.insert_lodge_tree(db, db_lodge=new_lodge)


def fetch_operator_managed_lodges(
        db: Session,
        operator_user: User,
        skip: int| None,
        limit: int | None,


):
    return crud_lodge_operator.get_active_lodges_for_operator(db, skip, limit, operator_id=operator_user.id)

def require_lodge_owner(db: Session, lodge_id: int, user_id: int) -> Lodge:
    """
    Verifies that the user legally owns the lodge (Legal Title Check).
    """
    lodge = crud_lodge.get(db, item_id=lodge_id)
    if not lodge or not lodge.is_owned_by(user_id):
        raise LodgeNotFoundError()
    return lodge


def require_lodge_operator(db: Session, lodge_id: int, user_id: int) -> Lodge:
    """
    Verifies that the user has an active operator assignment for this lodge.
    Universal single check for all day-to-day operations (Rooms, Leases, Payments, Approvals, Dashboard).
    """
    assignment = crud_lodge_operator.get_active_assignment(
        db, lodge_id=lodge_id, operator_id=user_id
    )
    if not assignment or not assignment.lodge:
        raise LodgeNotFoundError()

    return assignment.lodge


# Backward-compatibility aliases
verify_lodge_ownership = lambda db, lodge_id, landlord_id: require_lodge_owner(
    db=db, lodge_id=lodge_id, user_id=landlord_id
)
verify_lodge_access = lambda db, lodge_id, current_user: require_lodge_operator(
    db=db, lodge_id=lodge_id, user_id=current_user.id
)
verify_lodge_operational_access = require_lodge_operator


def user_can_access_room_lodge(room: Room, current_user: User, db: Session) -> bool:
    """
    Check if a user is an active operator for the lodge containing a specific room.
    """

    active_assignment = crud_lodge_operator.get_active_assignment(db, lodge_id=room.lodge_id, operator_id=current_user.id)
    return active_assignment is not None

def update_lodge_details(
    db: Session,
    lodge_id: int,
    update_data: LodgeUpdate,
    current_user: User
) -> Lodge:
    """
    Update details of a lodge.
    If the lodge is claimed, only the Landlord owner can update it.
    If the lodge is unclaimed, an active Operator can update it.
    """
    lodge = require_lodge_operator(db=db, lodge_id=lodge_id, user_id=current_user.id)

    if lodge.is_claimed and not lodge.is_owned_by(current_user.id):
        raise BaseNotAllowedError(entity_name='lodge owners')

    return crud_lodge.update(db=db, update_data=update_data, db_obj=lodge)
