"""
API routes for managing rooms.

Provides endpoints for landlords and operators to create, retrieve, and update rooms within lodges.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_operator_or_landlord_user
from app.models.user import User
from app.schemas import room as schema_room
from app.schemas.room import BulkRoomUpdate, RoomResponse
from app.schemas.error import ErrorResponseSchema
from app.services import room_service

router = APIRouter()


@router.get(
    '/{lodge_id}/rooms',
    response_model=List[schema_room.RoomResponse],
    summary="List all rooms in a lodge",
    description="Retrieves all rooms in a specific lodge with pagination.",
    response_description="List of rooms",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access"},
    },
)
def fetch_rooms_in_lodge(
    lodge_id: int,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):

    """
    Retrieve all rooms for an authorized lodge.
    """
    return room_service.get_lodge_rooms(
        db=db,
        lodge_id=lodge_id,
        current_user=current_user,
        skip=skip,
        limit=limit
    )


@router.post(
    '/',
    response_model=schema_room.RoomResponse,
    summary="Create a new room",
    description="Adds a new room to a lodge. Room numbers must be unique within the same lodge.",
    response_description="The newly created room",
    responses={
        400: {"model": ErrorResponseSchema, "description": "A room with this number already exists in the lodge"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access"},
    },
)
def create_room_in_lodge(
    room_in: schema_room.RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    Create a new room in a specific lodge.
    """
    return room_service.create_room_for_lodge(
        db=db,
        room_in=room_in,
        current_user=current_user
    )


@router.get(
    '/{room_id}',
    response_model=schema_room.RoomResponse,
    summary="Get room details",
    description="Retrieves details of a specific room. Accessible to any authenticated user who owns or manages the lodge.",
    response_description="Room details",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        404: {"model": ErrorResponseSchema, "description": "Room does not exist or the user does not have access to its lodge"},
    },
)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    Retrieve details of a specific room by its ID.
    """
    return room_service.get_room_details(
        db=db,
        room_id=room_id,
        current_user=current_user
    )


@router.patch(
    '/{room_id}',
    response_model=schema_room.RoomResponse,
    summary="Update room details",
    description="Updates room properties. Cannot update an occupied room — terminate the lease first. Room status can only be changed to allowed values.",
    response_description="Updated room details",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Cannot update an occupied room. Terminate the lease first / The provided room status is not a valid updatable option"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Room does not exist or user does not have access"},
    },
)
def update_room_by_id(
    room_id: int,
    update_data: schema_room.RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    Update details of a specific room.
    """
    return room_service.update_room_details(
        db=db,
        room_id=room_id,
        update_data=update_data,
        current_user=current_user
    )


@router.patch(
    '/{lodge_id}/rooms/bulk',
    response_model=List[RoomResponse],
    summary="Bulk update room base rent",
    description="Updates the base annual rent for multiple rooms at once. Rooms that are currently occupied cannot be updated.",
    response_description="List of updated rooms",
    responses={
        400: {"model": ErrorResponseSchema, "description": "One or more rooms in the batch are currently occupied"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can Rperform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access / No updatable rooms found or room count mismatch"},
    },
)
def bulk_update_room_base_rent(
    lodge_id: int,
    update_data: BulkRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    return room_service.bulk_update_base_rent(
        db=db,
        lodge_id=lodge_id,
        update_data=update_data,
        current_user=current_user
    )

