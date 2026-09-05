"""
Module providing lodge-related CRUD operations.

This module contains the CRUD operations for Lodge models.
"""
from sqlalchemy import or_, literal, func, select, and_, case
from sqlalchemy.orm import Session
from app.core.enums import RoomStatus, LeaseStatus, BadgeTexts, BadgeVariants, TenantStatus
from app.models.lease import Lease
from app.models.lodge import Lodge
from app.models.room import Room
from app.models.tenantprofile import TenantProfile
from app.models.user import User
from app.schemas.lodge import LodgeCreate, LodgeUpdate
from app.crud.base_crud import CRUDBase
from app.core import constants as const
from app.schemas.room import RoomCreate


class CRUDLodge(CRUDBase[Lodge, LodgeCreate, LodgeUpdate]):
    """
    CRUD class for Lodge model operations.
    """
    #method for getting lodge owned by a specific landlord
    def get_by_landlord(self, db: Session, landlord_id: int, lodge_id: int):
        """
        Get a specific lodge owned by a landlord.

        Args:
            db (Session): The database session.
            landlord_id (int): The ID of the landlord.
            lodge_id (int): The ID of the lodge.

        Returns:
            Lodge: The found lodge or None.
        """
        stmt = select(self.model).where(self.model.landlord_id == landlord_id, self.model.id == lodge_id)
        return db.execute(stmt).scalar()

    #method to getting lodge owned by a specific landlord with a specific lodge name
    def get_by_name_and_landlord(self, db: Session, landlord_id: int, lodge_name: str):
        """
        Get a lodge by its name and landlord ID.

        Args:
            db (Session): The database session.
            landlord_id (int): The ID of the landlord.
            lodge_name (str): The name of the lodge to search for.

        Returns:
            Lodge: The found lodge or None.
        """
        search = f'%{lodge_name}%'
        stmt = select(self.model).where(
            self.model.landlord_id == landlord_id,
            or_(
                self.model.name.ilike(search),
                literal(search).ilike(self.model.name.concat('%'))
            )
        )
        return db.execute(stmt).scalar()


    def get_by_name_and_creator(self, db: Session, creator_id: int, lodge_name: str):
        """
        Get an unclaimed lodge created by a specific operator by name.
        """
        search = f'%{lodge_name}%'
        stmt = select(self.model).where(
            self.model.created_by_user_id == creator_id,
            or_(
                self.model.name.ilike(search),
                literal(search).ilike(self.model.name.concat('%'))
            )
        )
        return db.execute(stmt).scalar()

    def bind_ownership(self, db: Session, lodge: Lodge, landlord_id: int) -> Lodge:
        """
        Bind legal ownership of a lodge to a landlord.
        """
        lodge.landlord_id = landlord_id
        db.commit()
        db.refresh(lodge)
        return lodge

    def relinquish_ownership(self, db: Session, lodge: Lodge) -> Lodge:
        """
        Relinquish legal ownership of a lodge, returning it to unclaimed state.
        """
        lodge.landlord_id = None
        db.commit()
        db.refresh(lodge)
        return lodge

    def get_lodges_by_owner(self, db: Session, landlord_id: int, skip: int = 0, limit: int = 20):
        """
        Get multiple lodges owned by a specific landlord.

        Args:
            db (Session): The database session.
            landlord_id (int): The ID of the landlord.
            skip (int, optional): Number of records to skip. Defaults to 0.
            limit (int, optional): Maximum number of records to return. Defaults to 100.

        Returns:
            List[Lodge]: A list of lodges owned by the landlord.
        """
        stmt = select(self.model).where( self.model.landlord_id == landlord_id).offset(skip).limit(limit)
        return db.execute(stmt).scalars().all()

    def get_room_status_counts(self, db: Session, lodge_id: int):
        """
        Get the count of rooms by status in a specific lodge.

        Args:
            db (Session): The database session.
            lodge_id (int): The ID of the lodge.

        Returns:
            RowMapping: The counts of occupied, vacant, and maintenance rooms.
        """
        occupied_count_expr = func.count(case((const.occupied_expr, 1), else_=None))

        vacant_count_expr = func.count(case((and_(*const.vacant_expr), 1), else_=None))

        maintenance_count_expr = func.count(case((and_(*const.maintenance_expr), 1), else_=None))

        total_rooms_count_expr = func.count(Room.id)

        stmt = select(

            total_rooms_count_expr.label('total_rooms'),
            occupied_count_expr.label('occupied'),
            vacant_count_expr.label('vacant'),
            maintenance_count_expr.label('maintenance')
        ).select_from(
            Room

        ).outerjoin(
            Lease,
            and_(
                Lease.room_id == Room.id,
            or_(
                Lease.status.is_(None),
                Lease.status.is_(LeaseStatus.PENDING_TERMINATION))
                 )
        ).where(
            Room.lodge_id == lodge_id
        )

        result = db.execute(stmt).mappings().first()

        return result

    def get_tenant_counts(self, db: Session, lodge_id: int):
        """
        Get the total number of tenants in a specific lodge.

        Args:
            db (Session): The database session.
            lodge_id (int): The ID of the lodge.

        Returns:
            RowMapping: The total tenant count.
        """
        tenant_count_expr = func.count(TenantProfile.id)
        stmt = select(tenant_count_expr.label('total_tenants')).where(
            TenantProfile.lodge_id == lodge_id,
            TenantProfile.status.is_(TenantStatus.APPROVED)
        )

        result = db.execute(stmt).mappings().first()
        return result

    def get_occupied_counts(self, db: Session, lodge_id: int):
        """
        Get the counts of occupied rooms categorized by payment/lease status.

        Args:
            db (Session): The database session.
            lodge_id (int): The ID of the lodge.

        Returns:
            RowMapping: The counts of safe, expiring, overdue, and owing statuses.
        """


        owing_count_expr = func.count(
            case(
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), 1), else_=None
            )
        )


        safe_count_expr = func.count(
            case(
                (and_(*const.filter_menu.get(BadgeTexts.SAFE)), 1), else_=None
            )
        )

        expiring_count_expr = func.count(
            case(
                (and_(*const.filter_menu.get(BadgeTexts.EXPIRING)), 1), else_=None
            )
        )

        overdue_expr = func.count(
            case(
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)), 1), else_=None
            )
        )

        pending_moveout_count_expr = func.count(
            case(
                (and_(*const.filter_menu.get(BadgeTexts.PENDING_MOVEOUT)), 1), else_=None
            )
        )

        stmt = select(
            safe_count_expr.label('safe'),
            expiring_count_expr.label('expiring'),
            overdue_expr.label('overdue'),
            pending_moveout_count_expr.label('pending_moveout'),
            owing_count_expr.label('owing')
        ).select_from(Lease).outerjoin(
            Room, Lease.room_id == Room.id
        ).outerjoin(
            const.PAYMENT_SUBQ, const.PAYMENT_SUBQ.c.lease_id == Lease.id
        ).where(
            Room.lodge_id == lodge_id,
            or_(
                Lease.status.is_(None),
                Lease.status == LeaseStatus.PENDING_TERMINATION
            ),
            Room.status.is_(None)
        )

        result = db.execute(stmt).mappings().first()
        return result

    def get_room_lease_info(
            self,
            db: Session,
            lease_id: int
    ):

        tenant_full_name = func.concat(User.first_name, ' ', User.last_name)
        stmt = select(
            Room.room_no.label('room_no'),
            Room.description.label('description'),
            Room.base_rent_price.label('base_rent'),
            Lease.start_date.label('start_date'),
            Lease.end_date.label('end_date'),
            Lease.agreed_rent_amt.label('agreed_rent'),
            const.per_lease_payment_total.label('total_paid'),
            const.remaining_balance_expr.label('remaining_balance'),
            tenant_full_name.label('name'),
            User.phone_no.label('phone'),
            const.days_left.label('days_left'),

            case(
                (and_(*const.filter_menu.get(BadgeTexts.PENDING_MOVEOUT)), BadgeTexts.PENDING_MOVEOUT.value),
                (and_(*const.filter_menu.get(BadgeTexts.SAFE)), BadgeTexts.SAFE.value),
                (and_(*const.filter_menu.get(BadgeTexts.EXPIRING)), BadgeTexts.EXPIRING.value),
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)), BadgeTexts.OVERDUE.value),
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), BadgeTexts.OWING.value),
                else_=BadgeTexts.UNKNOWN_BADGE_TEXT.value
            ).label('badge_text'),

            case(
                (and_(*const.filter_menu.get(BadgeTexts.PENDING_MOVEOUT)), BadgeVariants.PURPLE.value),
                (and_(*const.filter_menu.get(BadgeTexts.SAFE)), BadgeVariants.SUCCESS.value),
                (and_(*const.filter_menu.get(BadgeTexts.EXPIRING)), BadgeVariants.WARNING.value),
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)), BadgeVariants.ORANGE.value),
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), BadgeVariants.DANGER.value),
                else_=BadgeVariants.UNKNOWN_VARIANT.value
            ).label('badge_variant'),
        ).select_from(
            Lease
        ).join(
            self.model, Room.lodge_id == self.model.id
        ).join(
            Room, Lease.room_id == Room.id
        ).join(
            TenantProfile, Lease.tenant_id == TenantProfile.id
        ).join(
            User, TenantProfile.user_id == User.id
        ).outerjoin(
            const.PAYMENT_SUBQ, const.PAYMENT_SUBQ.c.lease_id == Lease.id
        ).where(
            Lease.id == lease_id,
            or_(
                Lease.status.is_(None),
                Lease.status != LeaseStatus.TERMINATED
            )
        ).group_by(

            Lease.id,
            Room.room_no,
            Room.description,
            Room.base_rent_price,
            Lease.start_date,
            Lease.end_date,
            Lease.agreed_rent_amt,
            User.first_name,
            User.last_name,
            const.PAYMENT_SUBQ.c.total_amt_paid
        )

        return db.execute(stmt).mappings().first()

    def insert_lodge_tree(self, db: Session, db_lodge: Lodge):
        db.add(db_lodge)
        db.commit()
        db.refresh(db_lodge)
        return db_lodge

    def get_tenant_dashboard_stats(self, db:Session, tenant_id: int, lodge_id: int,
                                   skip: int|None = 0, limit: int|None = 10):

        stmt = select(
            Lease.id,
            Room.room_no.label('room_no'),
            Room.description.label('description'),
            Room.base_rent_price.label('base_rent'),
            Lease.start_date.label('start_date'),
            Lease.end_date.label('end_date'),
            Lease.agreed_rent_amt.label('agreed_rent'),
            const.per_lease_payment_total.label('total_paid'),
            const.remaining_balance_expr.label('remaining_balance'),

            case(
                (and_(*const.filter_menu.get(BadgeTexts.PENDING_MOVEOUT)), BadgeTexts.PENDING_MOVEOUT.value),
                (and_(*const.filter_menu.get(BadgeTexts.SAFE)), BadgeTexts.SAFE.value),
                (and_(*const.filter_menu.get(BadgeTexts.EXPIRING)), BadgeTexts.EXPIRING.value),
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)), BadgeTexts.OVERDUE.value),
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), BadgeTexts.OWING.value),
                else_=BadgeTexts.UNKNOWN_BADGE_TEXT.value
            ).label('badge_text'),

            case(
                (and_(*const.filter_menu.get(BadgeTexts.PENDING_MOVEOUT)), BadgeVariants.PURPLE.value),
                (and_(*const.filter_menu.get(BadgeTexts.SAFE)), BadgeVariants.SUCCESS.value),
                (and_(*const.filter_menu.get(BadgeTexts.EXPIRING)), BadgeVariants.WARNING.value),
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)), BadgeVariants.ORANGE.value),
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), BadgeVariants.DANGER.value),
                else_=BadgeVariants.UNKNOWN_VARIANT.value
            ).label('badge_variant'),

            const.days_left.label('days_left')
        ).select_from(
            Lease,
        ).join(
            Room, Room.id == Lease.room_id
        ).outerjoin(
            TenantProfile, TenantProfile.id == Lease.tenant_id
        ).outerjoin(
            const.PAYMENT_SUBQ, const.PAYMENT_SUBQ.c.lease_id == Lease.id
        ).where(
            Room.lodge_id == lodge_id,
            or_(
                Lease.status.is_(None),
            Lease.status == LeaseStatus.PENDING_TERMINATION
            ),
            Lease.tenant_id == tenant_id
        ).group_by(
            Lease.id,
            Room.room_no,
            Room.description,
            Room.base_rent_price,
            Room.status,
            Lease.start_date,
            Lease.end_date,
            Lease.agreed_rent_amt,
            const.PAYMENT_SUBQ.c.total_amt_paid
        )

        stmt = stmt.offset(skip).limit(limit)

        return db.execute(stmt).mappings().all()

crud_lodge = CRUDLodge(Lodge)
