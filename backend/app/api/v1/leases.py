"""
API routes for managing leases.

Provides endpoints for creating, retrieving, updating, and terminating leases for landlords, operators, and tenants.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.enums import LeaseStatus
from app.schemas import lease as schema_lease
from app.schemas.error import ErrorResponseSchema
from app.api.deps import get_db, get_operator_or_landlord_user, get_tenant_user
from app.models.user import User
from app.services import lease_services

router = APIRouter()


@router.post(
    '/',
    response_model=schema_lease.LeaseResponse,
    summary="Create a new lease",
    description=(
        "Creates a lease agreement between a tenant and a room. "
        "The room must be vacant and the tenant must belong to the same lodge."
    ),
    response_description="The newly created lease",
    responses={
        400: {"model": ErrorResponseSchema, "description": "An active lease already exists for this room and tenant combination"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Room does not exist or user does not have access / Tenant does not exist or does not belong to this lodge"},
    },
)
def create_new_lease(
    lease_data: schema_lease.LeaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    Create a new lease.
    """
    return lease_services.create_new_lease_for_existing_tenant(
        db=db,
        lease_data=lease_data,
        current_user=current_user
    )


@router.get(
    '/{lodge_id}',
    response_model=List[schema_lease.LeaseHistoryResponse],
    summary="List leases for a lodge",
    description="Retrieves lease history for a lodge with optional filters by room, tenant, and status.",
    response_description="Filtered list of lease records",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access"},
    },
)
def get_leases_for_operator(
    lodge_id: int,
    room_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    status: Optional[LeaseStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):


    """
    Get all leases for an authorized lodge.
    """
    return lease_services.get_filtered_landlord_leases(
        db=db,
        current_user=current_user,
        lodge_id=lodge_id,
        tenant_id=tenant_id,
        room_id=room_id,
        skip=skip,
        max_limit=limit,
        status=status
    )


@router.get(
    '/tenant/me',
    response_model=List[schema_lease.LeaseHistoryResponse],
    summary="List my leases as tenant",
    description="Retrieves all leases for the currently authenticated tenant with optional status filter.",
    response_description="List of tenant's lease records",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only tenant accounts can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Tenant profile not found for the authenticated user"},
    },
)
def get_tenant_leases(
    skip: Optional[int] = None,
    max_limit: Optional[int] = None,
    status: Optional[LeaseStatus] = None,
    db: Session = Depends(get_db),
    tenant_user: User = Depends(get_tenant_user)
):
    """
    Get all leases for the currently authenticated tenant.
    """
    return lease_services.get_filtered_leases_tenant(
        db=db,
        tenant_profile=tenant_user.tenant_profile,
        skip=skip,
        max_limit=max_limit,
        status=status
    )


@router.patch(
    '/{lease_id}',
    response_model=schema_lease.LeaseResponse,
    summary="Update lease details",
    description="Updates an existing lease's properties such as rent amount or end date.",
    response_description="Updated lease details",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lease does not exist or user does not have access"},
    },
)
def update_lease_by_id(
    lease_id: int,
    lease_data: schema_lease.LeaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    Update details of an existing lease.
    """
    return lease_services.update_lease_details(
        db=db,
        lease_id=lease_id,
        update_data=lease_data,
        current_user=current_user
    )


@router.patch(
    '/terminate/{lease_id}',
    response_model=schema_lease.LeaseHistoryResponse,
    summary="Terminate a lease",
    description="Terminates an active lease and sets the room back to vacant.",
    response_description="Terminated lease details",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Lease is already terminated"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lease does not exist or user does not have access"},
    },
)
def terminate_lease_by_id(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):

    """
    Terminate a lease by its ID.
    """
    return lease_services.terminate_lease(
        db=db,
        lease_id=lease_id,
        current_user=current_user
    )


@router.patch(
    '/me/terminate/{lease_id}',
    response_model=schema_lease.LeaseHistoryResponse,
    summary="Request lease termination as tenant",
    description="Allows a tenant to request termination of their active lease.",
    response_description="Lease with updated pending termination status",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Lease is already terminated or already pending termination"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only tenant accounts can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lease does not exist or does not belong to the authenticated tenant"},
    },
)
def request_lease_termination(
    lease_id: int,
    db: Session = Depends(get_db),
    current_tenant: User = Depends(get_tenant_user)
):
    """
    Request the termination of an active lease by a tenant.
    """
    return lease_services.appeal_for_lease_termination(
        db=db,
        lease_id=lease_id,
        tenant_id=current_tenant.tenant_profile.id
    )
