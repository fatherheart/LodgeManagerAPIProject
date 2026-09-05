"""
Module providing payment-related business logic.

This module contains services for managing payments, supporting both Landlord and Operator operational management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.core.enums import LeaseStatus
from app.core.exceptions import (
    LeaseNotFoundError, RoomNotFoundError,
    InvalidLeaseActionError, RentAmtExceededError
)
from app.crud.payment import crud_payment
from app.crud.lease import crud_lease
from app.models.lease import Lease
from app.models.room import Room
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate
from app.services import lodge_service


def can_add_payment(total_payments: int, incoming_amt: int, agreed_amt: int) -> bool:
    """
    Check if a payment can be added based on the total payments and agreed amount.
    """
    return total_payments + incoming_amt <= agreed_amt


def add_payment_record(
    db: Session,
    payment_data: PaymentCreate,
    current_user: User
) -> Payment:
    """
    Add a new payment record by an authorized lodge manager.
    """
    options = joinedload(Lease.room).joinedload(Room.lodge)
    lease = crud_lease.get(db, payment_data.lease_id, options)

    if not lease or not lease.room or not lease.room.lodge:
        raise LeaseNotFoundError()

    lodge_service.verify_lodge_access(db=db, lodge_id=lease.room.lodge_id, current_user=current_user)

    if lease.status == LeaseStatus.TERMINATED:
        raise InvalidLeaseActionError(lease_status=lease.status)

    total_payments = crud_payment.get_payments_aggregate_by_lease_id(db, lease_id=lease.id)

    if not can_add_payment(
        total_payments=total_payments,
        incoming_amt=payment_data.amount_paid,
        agreed_amt=lease.agreed_rent_amt
    ):
        raise RentAmtExceededError(
            attempted=payment_data.amount_paid,
            current_total=total_payments,
            agreed=lease.agreed_rent_amt
        )

    return crud_payment.create(db, obj_in=payment_data)


def fetch_payments_by_lease(
    db: Session,
    lease_id: int,
    current_user: User,
    skip: Optional[int] = None,
    limit: Optional[int] = None
) -> List[Payment]:
    """
    Fetch payments for a specific lease.
    """
    options = joinedload(Lease.room).joinedload(Room.lodge)
    lease = crud_lease.get(db, lease_id, options)

    if not lease or not lease.room or not lease.room.lodge:
        raise LeaseNotFoundError()

    lodge_service.verify_lodge_access(db=db, lodge_id=lease.room.lodge_id, current_user=current_user)
    return crud_payment.get_lease_payments(db, lease_id=lease_id, skip=skip, limit=limit)


def fetch_tenant_lease_payments(
    db: Session,
    lease_id: int,
    tenant_id: int,
    skip: Optional[int] = None,
    limit: Optional[int] = None
) -> List[Payment]:
    """
    Fetch payments for a specific lease by a tenant.
    """
    from app.services.lease_services import verify_tenant_owns_lease

    lease = crud_lease.get(db, item_id=lease_id)
    if not lease:
        raise LeaseNotFoundError()

    if not verify_tenant_owns_lease(lease=lease, tenant_id=tenant_id):
        raise LeaseNotFoundError()

    return crud_payment.get_lease_payments(db, lease_id=lease_id, skip=skip, limit=limit)
