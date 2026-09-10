"""
API routes for managing tenants.

Provides endpoints for updating tenant profiles and fetching tenant details for landlords, operators, and tenants.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas import tenantprofile as schema_tenant
from app.schemas import lease as schema_lease
from app.schemas.error import ErrorResponseSchema
from app.api.deps import get_db, get_operator_or_landlord_user, get_tenant_user
from app.models.user import User
from app.services import tenant_services

router = APIRouter()


@router.patch(
    '/profiles/me',
    response_model=schema_tenant.TenantProfileResponse,
    summary="Update my tenant profile",
    description="Updates the authenticated tenant's profile information such as emergency contacts and student details.",
    response_description="Updated tenant profile",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only tenant accounts can perform this action"},
    },
)
def update_tenant_profile(
    tenant_data: schema_tenant.TenantProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_tenant_user)
):
    """
    Update the profile of the currently authenticated tenant.
    """
    return tenant_services.update_tenant_profile(
        db=db,
        update_data=tenant_data,
        base_user=current_user,
    )


@router.get(
    '/profile',
    response_model=schema_tenant.TenantProfileResponse,
    summary="Get my tenant profile",
    description="Retrieves the full profile of the currently authenticated tenant.",
    response_description="Tenant profile details",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only tenant accounts can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Tenant profile not found for the authenticated user"},
    },
)
def get_tenant_by_id(
    current_user: User = Depends(get_tenant_user)
):
    """
    Retrieve the profile of the currently authenticated tenant.
    """
    return tenant_services.fetch_tenant(current_user=current_user)


@router.get(
    '/profile/{tenant_id}',
    response_model=schema_tenant.TenantProfileResponse,
    summary="Get tenant profile by ID",
    description="Retrieves a specific tenant's profile for an authorized lodge manager.",
    response_description="Tenant profile details",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Tenant does not exist or user does not have access to its lodge"},
    },
)
def get_tenant_by_operator(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    Retrieve the profile of a specific tenant by an authorized manager.
    """
    return tenant_services.fetch_tenant_by_landlord(db=db, tenant_id=tenant_id, current_user=current_user)



@router.post(
    '/{tenant_id}/approve',
    response_model=schema_lease.LeaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Approve tenant onboarding application",
    description=(
        "Approves a tenant's onboarding application and atomically generates "
        "their lease and first upfront payment, setting the room status to OCCUPIED."
    ),
    response_description="Created lease agreement",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Invalid dates, payment exceeds rent, or room not available"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Tenant or room not found"},
    },
)
def approve_tenant(
    tenant_id: int,
    approval_data: schema_tenant.TenantApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    return tenant_services.approve_invited_tenant_application(
        db=db,
        tenant_id=tenant_id,
        current_user=current_user,
        approval_data=approval_data
    )


@router.post(
    '/{tenant_id}/reject',
    response_model=schema_tenant.TenantProfileResponse,
    summary="Reject tenant onboarding application",
    description="Rejects a tenant's onboarding application, leaving the room vacant.",
    response_description="Updated tenant profile with REJECTED status",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Tenant is not in pending status"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Tenant does not exist or user does not have access"},
    },
)
def reject_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    return tenant_services.reject_tenant_application(
        db=db,
        tenant_id=tenant_id,
        current_user=current_user
    )