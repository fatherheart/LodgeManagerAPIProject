"""
Module providing room-related CRUD operations.

This module contains the CRUD operations for Room models.
"""
from typing import Sequence

from app.core.enums import BadgeVariants, LeaseStatus, BadgeTexts, RoomStatus, TenantStatus
from app.models.lease import Lease
from app.models.lodge import Lodge
from app.models.room import Room
from app.models.tenantprofile import TenantProfile
from app.models.user import User
from app.schemas.dashboard import DashboardFilters
from app.schemas.room import RoomCreate, RoomUpdate, BulkRoomUpdate
from sqlalchemy.orm import Session, joinedload
from app.crud.base_crud import CRUDBase
from sqlalchemy import select, case, and_, func, RowMapping, or_
from app.core import constants as const
from utilities.dashboard_utilities import apply_dashboard_filters


class CRUDRoom(CRUDBase[Room, RoomCreate, RoomUpdate]):
    """
    CRUD class for Room model operations.
    """
    #method to get room by lodge and number
    # method to get many rooms in a lodge with pagination support

    def get_room_by_lodge_and_number(self, db: Session, room_no: str, lodge_id: int):
        """
        Retrieve a specific room by its room number.

        Args:
            db (Session): The database session.
            room_no (str): The room number.
            lodge_id (int): The ID of the lodge.

        Returns:
            Room: The found room or None.
        """
        stmt = select(self.model).where(
            self.model.lodge_id == lodge_id,
            self.model.room_no == room_no
        )
        return db.execute(stmt).scalar()

    def get_room_with_onboarding_state(self, db: Session, room_id: int):
        from sqlalchemy.orm import aliased
        from app.models.invitation import Invite
        from app.models.tenantprofile import TenantProfile
        from app.models.user import User
        from app.core.enums import InviteStatus, TenantStatus
        from datetime import datetime, timezone
        
        curr_time = datetime.now(timezone.utc).replace(tzinfo=None)

        active_invite = aliased(Invite)
        pending_invite = aliased(Invite)

        from sqlalchemy import literal

        stmt = (
            select(
                self.model,
                case(
                    (active_invite.id.is_not(None), literal(True)),
                    else_=literal(False)
                ).label('has_active_invite'),

                TenantProfile.id.label('tenant_id'),
                User.first_name,
                User.last_name,
                User.phone_no
            )
            .outerjoin(active_invite, and_(
                active_invite.room_id == self.model.id,
                active_invite.status == InviteStatus.SENT,
                active_invite.expires_at > curr_time
            ))
            .outerjoin(pending_invite, and_(
                pending_invite.room_id == self.model.id,
                pending_invite.status == InviteStatus.ACCEPTED
            ))
            .outerjoin(TenantProfile, and_(
                TenantProfile.id == pending_invite.accepted_by_tenant_id,
                TenantProfile.status == TenantStatus.PENDING
            ))
            .outerjoin(User, User.id == TenantProfile.user_id)
            .where(self.model.id == room_id)
            .options(joinedload(self.model.lodge))
        )

        return db.execute(stmt).first()


    def get_rooms(self, db: Session, lodge_id: int, skip: int = 0, max_limit: int = 50):
        """
        Retrieve a list of rooms for a lodge with pagination support.
        """
        stmt = select(self.model).where(self.model.lodge_id == lodge_id).offset(skip).limit(limit=max_limit)
        return list(db.execute(stmt).scalars().all())




    def get_dashboard_rooms(
            self,
            db: Session,
            filter_by: DashboardFilters,
            lodge_id: int,
            skip: int = 0,
            limit: int = 50
    ) -> Sequence[RowMapping]:
        """
        Retrieve rooms formatted for the dashboard with filters applied.

        Args:
            db (Session): The database session.
            filter_by (DashboardFilters): The filters to apply.
            lodge_id (int): The ID of the lodge.
            skip (int, optional): Number of records to skip. Defaults to 0.
            limit (int, optional): Maximum number of records to return. Defaults to 50.

        Returns:
            List[RowMapping]: A list of mapped rows containing dashboard room data.
        """

        stmt = (select(
            Lease.id.label('lease_id'),
            Room.id.label('room_id'),
            Room.room_no.label('room_no'),
            case(
                (and_(*const.filter_menu.get(BadgeTexts.PENDING_MOVEOUT)), BadgeTexts.PENDING_MOVEOUT.value),
                (and_(*const.filter_menu.get(BadgeTexts.SAFE)), BadgeTexts.SAFE.value),
                (and_(*const.filter_menu.get(BadgeTexts.EXPIRING)), BadgeTexts.EXPIRING.value),
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)), BadgeTexts.OVERDUE.value),
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), BadgeTexts.OWING.value),
                (and_(*const.vacant_expr), RoomStatus.VACANT.value),
                (and_(*const.maintenance_expr), RoomStatus.MAINTENANCE.value),
                else_=BadgeTexts.UNKNOWN_BADGE_TEXT.value
            ).label('badge_text'),

            case(
                (and_(*const.filter_menu.get(BadgeTexts.PENDING_MOVEOUT)), BadgeVariants.PURPLE.value),
                (and_(*const.filter_menu.get(BadgeTexts.SAFE)), BadgeVariants.SUCCESS.value),
                (and_(*const.filter_menu.get(BadgeTexts.EXPIRING)), BadgeVariants.WARNING.value),
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)), BadgeVariants.ORANGE.value),
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), BadgeVariants.DANGER.value),
                (and_(*const.vacant_expr), BadgeVariants.INFO.value),
                (and_(*const.maintenance_expr), BadgeVariants.INACTIVE.value),
                else_= BadgeVariants.UNKNOWN_VARIANT.value
            ).label('badge_variant'),

            case(
                (const.occupied_expr, func.concat(User.first_name, ' ', User.last_name, )),
                (and_(*const.vacant_expr), 'Ready to Lease'),
                (and_(*const.maintenance_expr), 'Unavailable'),
                else_='Invalid'
            ).label('main_display_text'),

            case(
                (and_(*const.filter_menu.get(BadgeTexts.OVERDUE)),
                    func.concat(func.abs(const.days_left, ), 'days overdue')
                ),
                (const.occupied_expr, func.concat(const.days_left, 'days left')),
                (and_(*const.vacant_expr), 'Available'),
                (and_(*const.maintenance_expr), 'Under Maintenance'),
                else_='Invalid'
            ).label('sub_display_text'),
            

            case(
                (and_(*const.filter_menu.get(BadgeTexts.OWING)), True),
                else_=False
            ).label('is_owing')

        ).select_from(
            Room
        ).outerjoin(
            Lease,
            and_(
                Room.id == Lease.room_id,
                or_(
                    Lease.status.is_(None),
                    Lease.status == LeaseStatus.PENDING_TERMINATION
                )

            )

        ).outerjoin(
            TenantProfile, and_(
                Lease.tenant_id == TenantProfile.id,
                TenantProfile.status.is_(TenantStatus.APPROVED)
            )
        ).outerjoin(
            User, TenantProfile.user_id == User.id
        ).outerjoin(
            const.PAYMENT_SUBQ, const.PAYMENT_SUBQ.c.lease_id == Lease.id
        ).where(
            Room.lodge_id == lodge_id
        ).group_by(
            Lease.id,
            Room.id,
            User.first_name,
            User.last_name,
            Room.room_no,
            Lease.agreed_rent_amt,
            Lease.end_date,

        ))

        filtered_stmt = apply_dashboard_filters(filter_by=filter_by, filters=const.filter_menu, stmt=stmt)

        stmt = filtered_stmt.offset(skip).limit(limit)

        return db.execute(stmt).mappings().all()

    def get_updatable_rooms(self, db: Session, lodge_id: int, room_ids: list[str]):
        stmt = select(self.model).where(
            self.model.lodge_id == lodge_id,
            and_(Room.id.in_(room_ids))
        )
        rooms: list[Room] =  list(db.execute(stmt).scalars().all())
        return rooms


crud_room = CRUDRoom(Room)
