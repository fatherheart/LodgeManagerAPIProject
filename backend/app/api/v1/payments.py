"""
API routes for managing payments.

Provides endpoints for creating payments and fetching payment histories for landlords, operators, and tenants.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas import payment as schema_payment
from app.schemas.error import ErrorResponseSchema
from app.api.deps import get_db, get_operator_or_landlord_user, get_tenant_user
from app.models.user import User
from app.services import payment_service

router = APIRouter()


@router.post(
    '/create-payment',
    response_model=schema_payment.PaymentResponse,
    summary="Record a rent payment",
    description=(
        "Records a payment against an active lease. "
        "The payment cannot exceed the remaining balance owed. "
        "Payments cannot be made against terminated leases."
    ),
    response_description="The recorded payment",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Cannot record a payment on a terminated lease / Payment amount exceeds the remaining balance"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lease does not exist or user does not have access"},
    },
)
def create_payment(
    payment_data: schema_payment.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    Create a new payment record.
    """
    return payment_service.add_payment_record(
        db=db,
        payment_data=payment_data,
        current_user=current_user
    )


@router.get(
    '/{lease_id}',
    response_model=List[schema_payment.PaymentResponse],
    summary="List payments for a lease",
    description="Retrieves all payment records for a specific lease.",
    response_description="List of payment records",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lease does not exist or user does not have access"},
    },
)
def get_payments(
    lease_id: int,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    """
    List all payments associated with a specific lease.
    """
    return payment_service.fetch_payments_by_lease(
        db=db,
        lease_id=lease_id,
        current_user=current_user,
        skip=skip,
        limit=limit
    )


@router.get(
    '/me/{lease_id}',
    response_model=List[schema_payment.PaymentResponse],
    summary="List my payments for a lease",
    description="Retrieves all payment records for a specific lease belonging to the authenticated tenant.",
    response_description="List of tenant's payment records",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only tenant accounts can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lease does not exist or does not belong to the authenticated tenant"},
    },
)
def list_my_lease_payments(
    lease_id: int,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    tenant_user: User = Depends(get_tenant_user)
):
    """
    List all payments for a lease owned by the authenticated tenant.
    """
    return payment_service.fetch_tenant_lease_payments(
        db=db,
        lease_id=lease_id,
        tenant_id=tenant_user.tenant_profile.id,
        skip=skip,
        limit=limit
    )
