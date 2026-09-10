"""
Module providing lease-related business logic.

This module contains services for managing leases, supporting both Landlord and Operator operational management.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.core.enums import LeaseStatus, TenantStatus
from app.crud.tenantprofile import crud_tenant
from app.models.lease import Lease
from app.models.room import Room
from app.models.tenantprofile import TenantProfile
from app.models.user import User
from app.schemas.lease import LeaseCreate, LeaseUpdate
from app.services import lodge_service, room_service
from app.crud.lease import crud_lease
from app.core.exceptions import (
    RoomNotFoundError, LeaseNotFoundError, InvalidLeaseActionError,
    TenantProfileNotFoundError, RentAmtExceededError, PendingTenantNotAllowed, InvalidActionError
)
from app.services.payment_service import can_add_payment


def create_new_lease_for_existing_tenant(
    db: Session,
    lease_data: LeaseCreate,
    current_user: User
) -> Lease:
    """
    Create a new lease for an existing tenant (APPROVED or previously REJECTED).
    """
    room = room_service.verify_room_existence(db=db, room_id=lease_data.room_id, current_user=current_user)

    tenant = crud_tenant.get(db, item_id=lease_data.tenant_id)
    if not tenant or room.lodge_id != tenant.lodge_id:
        raise TenantProfileNotFoundError()

    active_lease = crud_lease.get_active_lease_for_room(db, room_id=room.id)
    if active_lease:
        raise InvalidLeaseActionError(lease_status=active_lease.computed_status)

    if tenant.status not in (TenantStatus.APPROVED, TenantStatus.REJECTED):
        raise PendingTenantNotAllowed(tenant_id=tenant.id)


    return crud_lease.create_lease(db, lease_data=lease_data, tenant=tenant)


def get_filtered_landlord_leases(
    db: Session,
    lodge_id: int,
    current_user: User,
    tenant_id: Optional[int] = None,
    room_id: Optional[int] = None,
    skip: Optional[int] = None,
    max_limit: Optional[int] = None,
    status: Optional[LeaseStatus] = None
) -> List[Lease]:
    """
    Get filtered leases for an authorized lodge.
    """
    lodge_service.verify_lodge_access(db=db, lodge_id=lodge_id, current_user=current_user)

    return filter_leases(
        db,
        lodge_id=lodge_id,
        tenant_id=tenant_id,
        room_id=room_id,
        skip=skip,
        max_limit=max_limit,
        status=status
    )


def get_filtered_leases_tenant(
    db: Session,
    tenant_profile: TenantProfile,
    skip: Optional[int] = None,
    max_limit: Optional[int] = None,
    status: Optional[LeaseStatus] = None
) -> List[Lease]:
    """
    Get filtered leases for a specific tenant.
    """
    if not tenant_profile:
        raise TenantProfileNotFoundError()

    lodge = tenant_profile.lodge
    return filter_leases(
        db,
        tenant_id=tenant_profile.id,
        skip=skip,
        max_limit=max_limit,
        status=status,
        lodge_id=lodge.id if lodge else None
    )


def filter_leases(
    db: Session,
    lodge_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    room_id: Optional[int] = None,
    skip: Optional[int] = None,
    max_limit: Optional[int] = None,
    status: Optional[LeaseStatus] = None
) -> List[Lease]:
    return crud_lease.get_tenant_leases(
        db,
        lodge_id=lodge_id,
        tenant_id=tenant_id,
        room_id=room_id,
        status=status,
        max_limit=max_limit,
        skip=skip
    )


def verify_lease_to_terminate(db: Session, lease_id: int) -> Lease:
    options = [
        joinedload(Lease.room).joinedload(Room.lodge),
        joinedload(Lease.tenant).joinedload(TenantProfile.user)
    ]
    lease = crud_lease.get(db, lease_id, *options)

    if not lease:
        raise LeaseNotFoundError()

    if lease.status == LeaseStatus.TERMINATED:
        raise InvalidLeaseActionError(lease_status=lease.status)

    return lease


def terminate_lease(
    db: Session,
    lease_id: int,
    current_user: User
) -> Lease:
    """
    Terminate a specific lease by an authorized manager.
    """
    lease = verify_lease_to_terminate(db, lease_id=lease_id)
    lodge_service.verify_lodge_access(db=db, lodge_id=lease.room.lodge_id, current_user=current_user)
    return crud_lease.lease_terminate(db, db_lease=lease)


def update_lease_details(
    db: Session,
    lease_id: int,
    update_data: LeaseUpdate,
    current_user: User
) -> Lease:
    """
    Update details of a specific lease.
    """
    options = [
        joinedload(Lease.room).joinedload(Room.lodge),
        joinedload(Lease.tenant).joinedload(TenantProfile.user)
    ]
    lease = crud_lease.get(db, lease_id, *options)

    if not lease or not lease.room or not lease.room.lodge:
        raise LeaseNotFoundError()

    lodge_service.verify_lodge_access(db=db, lodge_id=lease.room.lodge_id, current_user=current_user)
    return crud_lease.update(db, db_obj=lease, update_data=update_data)


def appeal_for_lease_termination(
    db: Session,
    lease_id: int,
    tenant_id: int
) -> Lease:
    """
    Appeal to terminate a lease by a tenant.
    """
    lease = verify_lease_to_terminate(db, lease_id=lease_id)

    if not verify_tenant_owns_lease(lease=lease, tenant_id=tenant_id):
        raise LeaseNotFoundError()

    if lease.status == LeaseStatus.PENDING_TERMINATION:
        raise InvalidLeaseActionError(lease_status=lease.status)

    return crud_lease.request_terminate_lease(db, db_lease=lease)


def verify_tenant_owns_lease(lease: Lease, tenant_id: int) -> bool:
    return lease.tenant_id == tenant_id
