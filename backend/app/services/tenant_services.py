"""
Module providing tenant-related business logic.

This module contains services for managing tenants, applications, and profiles,
supporting both Landlord and Operator operational management.
"""
from sqlalchemy.orm import Session, joinedload

from app.crud.invite import crud_invite
from app.crud.user import crud_user
from app.crud.tenantprofile import crud_tenant
from app.core.enums import UserRole, InviteStatus, TenantStatus
from app.core.exceptions import (
    UserAlreadyExistError, TenantProfileNotFoundError,
    InviteNotFoundError, InvalidInvitation, InvalidActionError,
    RentAmtExceededError, InvalidLeaseActionError, RoomNotFoundError
)
from app.core.security import get_password_hash
from app.models.tenantprofile import TenantProfile
from app.models.user import User
from app.models.lease import Lease
from app.schemas.tenantprofile import TenantProfileCreate, TenantProfileUpdate, TenantApprovalCreate
from app.schemas.user import UserInternal
from app.services import lodge_service, room_service, user_service
from app.services.payment_service import can_add_payment
from app.crud.lease import crud_lease


def sign_up_tenant(
    db: Session,
    tenant_in: TenantProfileCreate,
) -> TenantProfile:
    """
    Sign up a new tenant via room invitation link.
    """
    invite_record = crud_invite.get_invite_record_by_id(db, invite_id=tenant_in.invite_id)
    
    if not invite_record:
        raise InviteNotFoundError(invite_id=tenant_in.invite_id)

    if invite_record.is_expired:
        raise InvalidInvitation(invite_status=InviteStatus.EXPIRED)

    if invite_record.status != InviteStatus.SENT:
        raise InvalidInvitation(invite_status=invite_record.status)

    tenant_internal_signup_data = user_service.setup_signup_data_internal(
        db, signup_data=tenant_in.user_info, role=UserRole.TENANT
    )

    return crud_tenant.create_tenant(
        db=db,
        tenant_in=tenant_in,
        internal_user=tenant_internal_signup_data,
        db_invite=invite_record
    )


def fetch_lodge_tenants(
    db: Session,
    lodge_id: int,
    current_user: User,
    skip: int = 0,
    limit: int = 50,
    status: TenantStatus | None = None
):
    """
    Fetch all tenants for an authorized lodge.
    """
    lodge_service.verify_lodge_access(db=db, lodge_id=lodge_id, current_user=current_user)
    return crud_tenant.get_tenants(db, lodge_id=lodge_id, skip=skip, max_limit=limit, status=status)


def update_tenant_profile(
    db: Session,
    base_user: User,
    update_data: TenantProfileUpdate
) -> TenantProfile:
    """
    Update a tenant's profile details.
    """
    tenant_profile = base_user.tenant_profile
    if not tenant_profile:
        raise TenantProfileNotFoundError()

    return crud_tenant.update_tenant(
        db=db,
        update_data=update_data,
        base_user=base_user,
        tenant_user=tenant_profile
    )


def fetch_tenant(current_user: User) -> TenantProfile:
    """
    Fetch the authenticated tenant's own profile.
    """
    tenant = current_user.tenant_profile
    if not tenant:
        raise TenantProfileNotFoundError()
    return tenant


def fetch_tenant_by_landlord(
    db: Session,
    tenant_id: int,
    current_user: User
) -> TenantProfile:
    """
    Fetch a tenant's profile by an authorized lodge manager (Landlord or Operator).
    """
    options = joinedload(TenantProfile.lodge)
    tenant = crud_tenant.get(db, tenant_id, options)

    if not tenant or not tenant.lodge:
        raise TenantProfileNotFoundError()

    lodge_service.verify_lodge_access(db=db, lodge_id=tenant.lodge_id, current_user=current_user)
    return tenant


def approve_invited_tenant_application(
    db: Session,
    tenant_id: int,
    current_user: User,
    approval_data: TenantApprovalCreate
) -> Lease:
    """
    Approve a tenant's onboarding application and atomically create a Lease + initial Payment.
    """
    options = [
        joinedload(TenantProfile.lodge),
        joinedload(TenantProfile.invite)
    ]
    tenant = crud_tenant.get(db, tenant_id, *options)

    if not tenant or not tenant.lodge:
        raise TenantProfileNotFoundError()

    lodge_service.verify_lodge_access(db=db, lodge_id=tenant.lodge_id, current_user=current_user)

    if tenant.status != TenantStatus.PENDING:
        raise InvalidActionError(error_name='Tenant Status', error_value=tenant.status.value)

    target_room_id = tenant.invite.room_id if tenant.invite else None
    if not target_room_id:
        raise RoomNotFoundError(detail="No room associated with this tenant application")

    room = room_service.verify_room_existence(db=db, room_id=target_room_id, current_user=current_user)

    active_lease = crud_lease.get_active_lease_for_room(db, room_id=room.id)
    if active_lease:
        raise InvalidLeaseActionError(lease_status=active_lease.computed_status)

    default_total_payments = 0
    if not can_add_payment(
        total_payments=default_total_payments,
        incoming_amt=approval_data.total_amt_paid,
        agreed_amt=approval_data.agreed_rent_amt
    ):
        raise RentAmtExceededError(
            attempted=approval_data.total_amt_paid,
            current_total=default_total_payments,
            agreed=approval_data.agreed_rent_amt
        )

    return crud_tenant.approve_and_create_lease(
        db,
        tenant=tenant,
        room_id=room.id,
        approval_data=approval_data
    )


def reject_tenant_application(
    db: Session,
    tenant_id: int,
    current_user: User
) -> TenantProfile:
    """
    Reject a pending tenant onboarding application.
    """
    options = joinedload(TenantProfile.lodge)
    tenant = crud_tenant.get(db, tenant_id, options)

    if not tenant or not tenant.lodge:
        raise TenantProfileNotFoundError()

    lodge_service.verify_lodge_access(db=db, lodge_id=tenant.lodge_id, current_user=current_user)

    if tenant.status != TenantStatus.PENDING:
        raise InvalidActionError(error_name='Tenant Status', error_value=tenant.status.value)

    return crud_tenant.reject_tenant(db, tenant=tenant)
