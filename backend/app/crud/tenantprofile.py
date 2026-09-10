"""
Module providing tenant profile-related CRUD operations.

This module contains the CRUD operations for TenantProfile models.
"""
from typing import Dict, Any, Optional

from sqlalchemy import select

from app.core.enums import InviteStatus, TenantStatus
from app.models.invitation import Invite
from app.models.tenantprofile import TenantProfile
from app.models.user import User
from app.models.lease import Lease
from app.models.payment import Payment
from app.schemas.tenantprofile import TenantProfileCreate, TenantProfileUpdate, TenantInfoUpdate, TenantApprovalCreate
from sqlalchemy.orm import Session
from app.crud.base_crud import CRUDBase, ModelType
from app.schemas.user import  UserInternal, UserUpdate


class CRUDTenantProfile(CRUDBase[TenantProfile, TenantProfileCreate, TenantProfileUpdate]):
    """
    CRUD class for TenantProfile model operations.
    """
    _USER_UPDATE_FIELDS = {'first_name', 'last_name', 'phone_no', 'email'} # email update will be by a security feature
    _TENANT_UPDATE_FIELDS = {'emergency_contact_name', 'emergency_contact_phone_no', 'level', 'reg_no', 'department'
                             'tenant_type'} #other specific fields for specific tenants will also be a security feature

    def create_tenant(self, db: Session, tenant_in: TenantProfileCreate, internal_user: UserInternal,
                      db_invite: Invite):
        """
        Create a new tenant and associated user profile.

        Args:
            db_invite(Invite): The invite record that was used for the tenant invitation
            db (Session): The database session.
            tenant_in (TenantProfileCreate): The tenant creation data.
            internal_user (UserInternal): The internal user data.

        Returns:
            TenantProfile: The newly created tenant profile.
        """
        db_user = User(**internal_user.model_dump())
        db_tenant = self.model(**tenant_in.tenant_info.model_dump(), lodge_id=db_invite.lodge_id)
        db_user.tenant_profile = db_tenant
        db.add(db_user)
        db.flush()
        db_invite.accepted_by_tenant = db_tenant
        db_invite.status = InviteStatus.ACCEPTED
        db.commit()
        db.refresh(db_tenant)
        return db_tenant

    def get_tenants(self, db: Session, lodge_id: int, skip: int = 0, max_limit:int =50, status: TenantStatus|None= None):
        """
        Get a list of tenants in a specific lodge. filters on the status can be applied

        Args:
            status(TenantStatus, optional): The status to filter by. Defaults to None
            db (Session): The database session.
            lodge_id (int): The ID of the lodge.
            skip (int, optional): Number of records to skip. Defaults to 0.
            max_limit (int, optional): Maximum number of records to return. Defaults to 50.

        Returns:
            list[type[TenantProfile]]: A list of retrieved tenant profiles.
        """
        stmt = select(TenantProfile).where(
            self.model.lodge_id == lodge_id
        ).offset(skip).limit(max_limit)

        if status:
            stmt = stmt.where(TenantProfile.status == status)

        tenants: list[TenantProfile] =  list(db.execute(stmt).scalars().all())
        return tenants


    def update_tenant(self, db: Session, update_data: TenantProfileUpdate, base_user: User,
                      tenant_user: TenantProfile) -> ModelType:
        """
        Update an existing tenant profile and associated user profile.

        Args:
            db (Session): The database session.
            update_data (TenantProfileUpdate): The updated tenant data.
            base_user (User): The associated base user object.
            tenant_user (TenantProfile): The tenant profile object to update.

        Returns:
            ModelType: The updated tenant profile.
        """

        user_data_dict = update_data.user_info.model_dump(exclude_unset=True) if isinstance(update_data.user_info, UserUpdate) else {}
        tenant_profile_dict = update_data.tenant_info.model_dump(exclude_unset=True) if isinstance(update_data.tenant_info, TenantInfoUpdate) else {}

        try:

            for field in self._USER_UPDATE_FIELDS:
                if field in user_data_dict:
                    setattr(base_user, field, user_data_dict[field])

            db.add(base_user)

            for field in self._TENANT_UPDATE_FIELDS:
                if field in tenant_profile_dict:
                    setattr(tenant_user, field, tenant_profile_dict[field])

            db.add(tenant_user)

            db.commit()
            db.refresh(tenant_user)
            return tenant_user

        except Exception as e:
            db.rollback()
            raise e

    def approve_and_create_lease(
        self,
        db: Session,
        tenant: TenantProfile,
        room_id: int,
        approval_data: TenantApprovalCreate
    ) -> Lease:
        """
        Atomically approve a tenant profile, generate their lease, and record initial payment.

        Args:
            db (Session): The database session.
            tenant (TenantProfile): The tenant profile being approved.
            room_id (int): The ID of the room being assigned.
            approval_data (TenantApprovalCreate): Explicit lease terms and payment amount.

        Returns:
            Lease: The newly created lease.
        """
        db_lease = Lease(
            tenant_id=tenant.id,
            room_id=room_id,
            start_date=approval_data.start_date,
            end_date=approval_data.end_date,
            agreed_rent_amt=approval_data.agreed_rent_amt
        )

        if approval_data.total_amt_paid > 0:
            db_payment = Payment(amount_paid=approval_data.total_amt_paid)
            db_lease.payments.append(db_payment)

        tenant.status = TenantStatus.APPROVED

        try:
            db.add(db_lease)
            db.add(tenant)
            db.commit()
            db.refresh(db_lease)
            return db_lease
        except Exception as e:
            db.rollback()
            raise e

    def reject_tenant(self, db: Session, tenant: TenantProfile) -> TenantProfile:
        """
        Reject a tenant application and persist status in database.

        Args:
            db (Session): The database session.
            tenant (TenantProfile): The tenant profile being rejected.

        Returns:
            TenantProfile: The updated tenant profile.
        """
        tenant.status = TenantStatus.REJECTED
        try:
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            return tenant
        except Exception as e:
            db.rollback()
            raise e


crud_tenant = CRUDTenantProfile(TenantProfile)
