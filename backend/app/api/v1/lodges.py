"""
API routes for managing lodges.

Provides endpoints for landlords to register, retrieve, update lodges, and view tenants.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user

from app.api.deps import get_db, get_landlord_user, get_current_user, get_operator_or_landlord_user
from app.core.enums import TenantStatus
from app.schemas import lodge as lodge_schema
from app.schemas import tenantprofile as schema_tenant
from app.schemas.error import ErrorResponseSchema
from app.models.user import User
from app.crud.lodge import crud_lodge
from app.schemas.lodge import LodgeResponse
from app.schemas.lodge_operator import LodgeOperatorResponse
from app.services import lodge_service, tenant_services, operator_invite_service

router = APIRouter()



@router.post(
    '/register',
    response_model=lodge_schema.LodgeResponse,
    summary="Register a new lodge",
    description="Creates a new lodge for the authenticated landlord. A lodge name must be unique per landlord.",
    response_description="The newly registered lodge",
    responses={
        400: {"model": ErrorResponseSchema, "description": "A lodge with this name already exists for this landlord"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only landlord accounts can perform this action"},
    },
)
def register_lodge_for_landlord(
    lodge_in: lodge_schema.LodgeCreate,
    db: Session = Depends(get_db),
    landlord_user: User = Depends(get_landlord_user)
):
    """
    Register a new lodge for the authenticated landlord.
    """
    return lodge_service.create_new_lodge_for_authorized_user(
        db=db,
        current_user=landlord_user,
        lodge_data=lodge_in
    )




@router.post(
    '/register/operator-pilot',
    response_model=lodge_schema.LodgeResponse,
    status_code=200,
    summary="Register a new lodge for a pilot operator",
    description="Creates a new lodge for the authenticated operator. A lodge name must be unique per operator.",
    response_description="The newly registered lodge",
    responses={
        400: {"model": ErrorResponseSchema, "description": "A lodge with this name already exists"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only operators can perform this action"},
    },
)
def register_lodge_for_pilot_operator(
    lodge_in: lodge_schema.LodgeCreate,
    db: Session = Depends(get_db),
    operator_user: User = Depends(get_operator_or_landlord_user)
):

    return lodge_service.create_new_lodge_for_authorized_user(
        db=db,
        current_user=operator_user,
        lodge_data=lodge_in
    )


@router.get(
    '/{lodge_id}',
    response_model=lodge_schema.LodgeResponse,
    summary="Get lodge by ID",
    description="Retrieves details of a specific lodge.",
    response_description="Lodge details",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access"},
    },
)
def get_lodge_by_id(
    lodge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific lodge by its ID.
    """
    return lodge_service.verify_lodge_access(db=db, lodge_id=lodge_id, current_user=current_user)


@router.get(
    '/',
    response_model=List[lodge_schema.LodgeResponse],
    summary="List all lodges for landlord",
    description="Retrieves all lodges owned by the authenticated landlord with pagination.",
    response_description="List of lodges",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only landlord accounts can perform this action"},
    },
)
def get_lodges_by_landlord(
    db: Session = Depends(get_db),
    landlord_user: User = Depends(get_landlord_user),
    skip: int = 0,
    limit: int = 20
):
    """
    Retrieve all lodges owned by the authenticated landlord.
    """
    return crud_lodge.get_lodges_by_owner(db=db, landlord_id=landlord_user.id, skip=skip, limit=limit)


@router.get(
    '/operator-lodges',
    response_model=List[lodge_schema.LodgeResponse],
    summary="List all lodges managed by operator",
    description="Retrieves all lodges managed by the authenticated operator with pagination.",
    response_description="List of lodges",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only operators can perform this action"},
    },
)

def get_operator_lodges(
    db: Session = Depends(get_db),
    operator_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20
):

    return lodge_service.fetch_operator_managed_lodges(db, operator_user, skip, limit)

@router.get(
    '/{lodge_id}/tenants',
    response_model=List[schema_tenant.TenantProfileResponse],
    summary="List tenants in a lodge",
    description="Retrieves all tenants assigned to a specific lodge.",
    response_description="List of tenant profiles",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access"},
    },
)
def get_lodge_tenants(
    lodge_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[TenantStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    """
    Retrieve all tenants in a specific lodge.
    """
    return tenant_services.fetch_lodge_tenants(
        db=db,
        lodge_id=lodge_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        status=status
    )


@router.patch(
    '/{lodge_id}',
    response_model=lodge_schema.LodgeResponse,
    summary="Update lodge details",
    description="Updates the name or address of a specific lodge. Only the owning landlord can update if claimed.",
    response_description="Updated lodge details",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access"},
    },
)
def update_lodge_details(
    lodge_id: int,
    update_data: lodge_schema.LodgeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update details of an existing lodge.
    """
    return lodge_service.update_lodge_details(
        db=db,
        lodge_id=lodge_id,
        update_data=update_data,
        current_user=current_user
    )


@router.patch(
    '/{lodge_id}/operators/{operator_id}',
    response_model=LodgeOperatorResponse,
    summary="Revoke an operator from a lodge",
    description="Allows the lodge owner to revoke an active operator's management access.",
    response_description="The updated lodge operator junction record",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Operator is not actively assigned to this lodge"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only the lodge owner can revoke operators"},
        404: {"model": ErrorResponseSchema, "description": "Lodge not found"},
    },
)
def revoke_operator(
    lodge_id: int,
    operator_id: int,
    db: Session = Depends(get_db),
    landlord_user: User = Depends(get_landlord_user)
):
    return operator_invite_service.revoke_operator(
        db=db,
        lodge_id=lodge_id,
        operator_id=operator_id,
        current_user=landlord_user
    )


