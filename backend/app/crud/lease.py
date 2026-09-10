"""
Module providing lease-related CRUD operations.

This module contains the CRUD operations for Lease models.
"""
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from app.core.enums import LeaseStatus, TenantStatus
from app.models.payment import Payment
from app.models.room import RoomStatus, Room
from app.models.tenantprofile import TenantProfile
from app.schemas.lease import LeaseCreate, LeaseUpdate
from app.models.lease import Lease
from app.crud.base_crud import CRUDBase
from datetime import datetime, date
from sqlalchemy import select, or_


class CRUDLease(CRUDBase[Lease, LeaseCreate, LeaseUpdate]):
    """
    CRUD class for Lease model operations.
    """

    def get_tenant_leases(
            self,
            db: Session,
            lodge_id: Optional[int] = None,
            tenant_id: Optional[int] = None,
            room_id: Optional[int] = None,
            status: Optional[LeaseStatus] = None,
            skip: Optional[int] = None,
            max_limit: Optional[int] = None
    ) -> list[Lease]:
        """
        Get leases for a tenant with optional filtering.

        Args:
            db (Session): The database session.
            lodge_id (Optional[int]): The ID of the lodge. Defaults to None.
            tenant_id (Optional[int]): The ID of the tenant. Defaults to None.
            room_id (Optional[int]): The ID of the room. Defaults to None.
            status (Optional[LeaseStatus]): The status of the lease. Defaults to None.
            skip (Optional[int]): Number of records to skip. Defaults to None.
            max_limit (Optional[int]): Maximum number of records to return. Defaults to None.

        Returns:
            list[Lease]: A list of retrieved leases.
        """

        # 1. Initialize the statement
        stmt = select(self.model).join(TenantProfile).join(Room)

        if tenant_id:
            stmt = stmt.where(TenantProfile.id == tenant_id)

        if room_id:
            stmt = stmt.where(Room.id == room_id)

        if status:
            stmt = stmt.where(Lease.status == status)

        stmt = stmt.where(Room.lodge_id == lodge_id).offset(skip).limit(max_limit)
        lease_option = [joinedload(self.model.room), joinedload(self.model.tenant).joinedload(TenantProfile.user)]
        stmt = stmt.options(*lease_option)

        # 4. Execute
        result = db.execute(stmt)
        leases: list[Lease] = list(result.scalars().all())
        return leases


    def create_lease(self, db: Session, lease_data: LeaseCreate, tenant: Optional[TenantProfile] = None):
        """
        Create a new lease and associated initial payment.
        If the tenant was previously REJECTED, atomically flips their status to APPROVED.

        Args:
            db (Session): The database session.
            lease_data (LeaseCreate): The lease creation data.
            tenant (Optional[TenantProfile]): The tenant profile associated with the lease.

        Returns:
            Lease: The newly created lease.
        """
        db_lease = self.model(**lease_data.model_dump(exclude={'total_amt_paid'}))
        if lease_data.total_amt_paid > 0:
            db_payment = Payment(amount_paid=lease_data.total_amt_paid)
            db_lease.payments.append(db_payment)

        try:
            if tenant and tenant.status == TenantStatus.REJECTED:
                tenant.status = TenantStatus.APPROVED
                db.add(tenant)

            db.add(db_lease)
            db.commit()
            db.refresh(db_lease)
            return db_lease
        except Exception as e:
            db.rollback()
            raise e

    def get_active_lease_for_room(self, db: Session, room_id: int):
        """
        Get an active lease for a specific room

        Args:
            db (Session): The database session.
            room_id (int): The ID of the room.

        Returns:
            Lease: The active lease(even if overdue) or None.
        """
        stmt =  select(self.model).where(
            self.model.room_id == room_id,
            or_(
                self.model.status.is_(None),
                self.model.status == LeaseStatus.PENDING_TERMINATION
        ))
        return db.execute(stmt).scalar_one_or_none()

    def lease_terminate(self, db: Session, db_lease: Lease) -> Lease:
        """
        Terminate an active lease.

        Args:
            db (Session): The database session.
            db_lease (Lease): The lease to terminate.

        Returns:
            Lease: The terminated lease.
        """
        db_lease.status = LeaseStatus.TERMINATED
        db_lease.end_date = datetime.now()
        db.commit()
        db.refresh(db_lease)
        return db_lease



    def request_terminate_lease(self, db: Session, db_lease: Lease) -> Lease:
        """
        Request termination for a lease.

        Args:
            db (Session): The database session.
            db_lease (Lease): The lease to request termination for.

        Returns:
            Lease: The updated lease.
        """
        db_lease.status = LeaseStatus.PENDING_TERMINATION
        db.commit()
        db.refresh(db_lease)
        return db_lease

    def has_active_lease(self, db: Session, tenant_id: int) -> bool:
        """
        Check if a tenant currently has any active (un-terminated) lease.
        Uses SQL EXISTS for O(1) early-exit evaluation at the database engine level.
        """
        stmt = select(
            select(self.model.id)
            .where(
                self.model.tenant_id == tenant_id,
                or_(
                    self.model.status.is_(None),
                    self.model.status != LeaseStatus.TERMINATED
                )
            )
            .exists()
        )
        return bool(db.execute(stmt).scalar())


crud_lease = CRUDLease(Lease)
