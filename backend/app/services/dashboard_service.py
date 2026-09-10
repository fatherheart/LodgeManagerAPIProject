"""
Module providing dashboard-related business logic.

This module contains services for generating operational and financial dashboard summaries
for both Landlords and Operators.
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.exceptions import LeaseNotFoundError, LodgeNotFoundError
from app.crud.lodge import crud_lodge
from app.models.room import RoomFilter
from app.models.user import User
from app.crud.payment import crud_payment
from app.schemas.dashboard import (
    LandlordDashboardStats, DashboardFilters, RoomSummary,
    LeaseSummary, FinancialSummary, TenantSummary,
    RoomLeaseInfo, TenantDashboardStats
)
from app.schemas.entity_count import EntityCountResponse, OccupiedCounts
from app.schemas.financial import FinancialResponse
from app.schemas.lease import OccupiedRoomLeasesResponse
from app.crud.room import crud_room
from app.schemas.room import RoomStatusCounts, RoomGridSummary
from app.services import lodge_service
from app.core.enums import RoomStatus, BadgeTexts


def get_financial_summary(db: Session, lodge_id: int, filter_by: DashboardFilters) -> FinancialResponse:
    """
    Get financial summary for a specific lodge.
    """
    potential_revenue = crud_payment.get_potential_income_from_rooms(db, lodge_id=lodge_id)
    active_lease_financials = crud_payment.get_financials_for_active_leases(db, lodge_id=lodge_id, filter_by=filter_by)
    forecasted_revenue = crud_payment.get_financial_for_forecasted_empty_rooms(db, lodge_id=lodge_id, filter_by=filter_by)
    unpaid_rent = crud_payment.get_total_unpaid_rent(db, lodge_id=lodge_id, filter_by=filter_by)

    return FinancialResponse(
        potential_revenue=potential_revenue,
        expected_revenue=active_lease_financials.get('expected_revenue'),
        collected_revenue=active_lease_financials.get('collected_revenue'),
        forecasted_revenue=forecasted_revenue,
        unpaid_rent=unpaid_rent
    )


def get_room_dashboard_summary(
    db: Session,
    lodge_id: int,
    rooms: RoomFilter,
    filter_by: DashboardFilters,
    skip: Optional[int] = None,
    limit: Optional[int] = None
) -> OccupiedRoomLeasesResponse:
    """
    Get a dashboard summary of rooms in a specific lodge.
    """
    raw_rooms = crud_room.get_dashboard_rooms(
        db=db,
        filter_by=filter_by,
        lodge_id=lodge_id,
        skip=skip,
        limit=limit,
    )
    room_grids = [RoomGridSummary(**row) for row in raw_rooms]

    rooms.safe = [room for room in room_grids if room.badge_text == BadgeTexts.SAFE]
    rooms.expiring = [room for room in room_grids if room.badge_text == BadgeTexts.EXPIRING]
    rooms.overdue = [room for room in room_grids if room.badge_text == BadgeTexts.OVERDUE]
    rooms.pending_moveout = [room for room in room_grids if room.badge_text == BadgeTexts.PENDING_MOVEOUT]
    rooms.owing = [
        room for room in room_grids
        if room.badge_text == BadgeTexts.OWING or (room.badge_text == BadgeTexts.PENDING_MOVEOUT and room.is_owing)
    ]

    # vacant rooms
    rooms.vacant = [room for room in room_grids if room.badge_text == RoomStatus.VACANT]
    # maintenance rooms
    rooms.maintenance = [room for room in room_grids if room.badge_text == RoomStatus.MAINTENANCE]

    return OccupiedRoomLeasesResponse(
        safe=rooms.safe,
        expiring=rooms.expiring,
        overdue=rooms.overdue,
        pending_moveout=rooms.pending_moveout,
        owing=rooms.owing
    )



def get_entity_count_summary(db: Session, lodge_id: int) -> EntityCountResponse:
    """
    Get entity counts (total rooms, tenants, room status counts) for a specific lodge.
    """
    total_entity_counts = EntityCountResponse(
        total_rooms=0,
        total_tenants=0,
        room_status_counts=RoomStatusCounts(**{'occupied': 0, 'vacant': 0, 'maintenance': 0}),
        occupied_counts=OccupiedCounts(**{'safe': 0, 'expiring': 0, 'overdue': 0, 'pending_moveout': 0, 'owing': 0}),
        occupancy_rate=0
    )

    room_status_counts = crud_lodge.get_room_status_counts(db, lodge_id=lodge_id)
    if room_status_counts:
        total_entity_counts.total_rooms = room_status_counts.get('total_rooms')
        total_entity_counts.room_status_counts.occupied = room_status_counts.get('occupied')
        total_entity_counts.room_status_counts.vacant = room_status_counts.get('vacant')
        total_entity_counts.room_status_counts.maintenance = room_status_counts.get('maintenance')

    tenant_counts = crud_lodge.get_tenant_counts(db, lodge_id=lodge_id)
    if tenant_counts:
        total_entity_counts.total_tenants = tenant_counts.get('total_tenants')

    occupied_counts = crud_lodge.get_occupied_counts(db, lodge_id=lodge_id)
    if occupied_counts:
        total_entity_counts.occupied_counts.safe = occupied_counts.get('safe')
        total_entity_counts.occupied_counts.expiring = occupied_counts.get('expiring')
        total_entity_counts.occupied_counts.overdue = occupied_counts.get('overdue')
        total_entity_counts.occupied_counts.pending_moveout = occupied_counts.get('pending_moveout')
        total_entity_counts.occupied_counts.owing = occupied_counts.get('owing')

    if total_entity_counts.total_rooms > 0:
        rate = (total_entity_counts.room_status_counts.occupied / total_entity_counts.total_rooms) * 100
        total_entity_counts.occupancy_rate = int(rate)

    return total_entity_counts


def get_landlord_dashboard(
    db: Session,
    lodge_id: int,
    current_user: User,
    filter_by: DashboardFilters,
    skip: Optional[int] = None,
    limit: Optional[int] = None
) -> LandlordDashboardStats:
    """
    Get operational and financial dashboard statistics for an authorized lodge manager.
    """
    lodge_service.verify_lodge_access(db=db, lodge_id=lodge_id, current_user=current_user)

    financials = get_financial_summary(db, lodge_id=lodge_id, filter_by=filter_by)
    entity_count = get_entity_count_summary(db, lodge_id=lodge_id)

    rooms = RoomFilter()
    occupied_rooms_lease = get_room_dashboard_summary(
        db, lodge_id=lodge_id, rooms=rooms, filter_by=filter_by,
        skip=skip, limit=limit
    )


    return LandlordDashboardStats(
        financials=financials,
        entity_counts=entity_count,
        occupied_rooms_lease=occupied_rooms_lease,
        maintenance_rooms=rooms.maintenance,
        vacant_rooms=rooms.vacant,
    )


def _organise_room_lease_summary(
    db: Session,
    current_user: User,
    lease_id: int
) -> RoomLeaseInfo:
    from app.crud.lease import crud_lease
    from app.models.lease import Lease
    from app.models.room import Room
    from sqlalchemy.orm import joinedload

    options = [joinedload(Lease.room).joinedload(Room.lodge)]
    lease = crud_lease.get(db, lease_id, *options)
    if not lease or not lease.room or not lease.room.lodge:
        raise LeaseNotFoundError()

    lodge_service.verify_lodge_access(db=db, lodge_id=lease.room.lodge_id, current_user=current_user)

    raw_summary_row = crud_lodge.get_room_lease_info(
        db,
        lease_id=lease_id
    )

    if not raw_summary_row:
        raise LeaseNotFoundError()

    room_summary = RoomSummary(**raw_summary_row, status=RoomStatus.OCCUPIED)
    lease_summary = LeaseSummary(**raw_summary_row)
    financial_summary = FinancialSummary(**raw_summary_row)
    tenant_summary = TenantSummary(**raw_summary_row)
    
    return RoomLeaseInfo(
        room=room_summary,
        lease=lease_summary,
        tenant=tenant_summary,
        finance=financial_summary,
        badge_text=raw_summary_row.get('badge_text'),
        badge_variant=raw_summary_row.get('badge_variant'),
    )


def get_dashboard_lease_info(
    db: Session,
    lease_id: int,
    current_user: User
) -> RoomLeaseInfo:
    return _organise_room_lease_summary(
        db=db,
        current_user=current_user,
        lease_id=lease_id
    )


def get_tenant_active_lease_stats(
    db: Session,
    tenant_id: int,
    lodge_id: int,
    skip: Optional[int] = None,
    limit: Optional[int] = None
) -> List[TenantDashboardStats]:
    row_summary_list = crud_lodge.get_tenant_dashboard_stats(
        db,
        tenant_id=tenant_id,
        lodge_id=lodge_id,
        skip=skip,
        limit=limit
    )
    if not row_summary_list:
        return []

    tenant_stat_list: List[TenantDashboardStats] = []
    for row in row_summary_list:
        room_summary = RoomSummary(**row, status=RoomStatus.OCCUPIED)
        lease_summary = LeaseSummary(**row)
        financial_summary = FinancialSummary(**row)

        stat = TenantDashboardStats(
            room=room_summary,
            lease=lease_summary,
            finance=financial_summary,
            badge_text=row.get('badge_text'),
            badge_variant=row.get('badge_variant'),
        )
        tenant_stat_list.append(stat)

    return tenant_stat_list
