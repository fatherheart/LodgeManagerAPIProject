"""
API routes for lodge dashboards.

Provides endpoints to retrieve dashboard statistics and summaries for landlords and operators.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_operator_or_landlord_user, get_db
from app.core.enums import RoomStatus, BadgeTexts
from app.models.user import User
from app.schemas import dashboard as schema_dashboard
from app.schemas.dashboard import DashboardFilters, RoomLeaseInfo
from app.schemas.error import ErrorResponseSchema
from app.services import dashboard_service

router = APIRouter()


@router.get(
    '/me/landlord/{lodge_id}',
    response_model=schema_dashboard.LandlordDashboardStats,
    summary="Get lodge dashboard statistics",
    description="Retrieves comprehensive dashboard statistics for a specific lodge including financials, entity counts, and room occupancy breakdown.",
    response_description="Complete dashboard statistics",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user does not have access"},
    },
)
def get_operator_dashboard(
    lodge_id: int,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    room_statuses: List[RoomStatus] = Query(default=[]),
    financial_filters: List[BadgeTexts] = Query(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user),
):

    """
    Retrieve operational dashboard statistics for a specific lodge.
    """

    all_filters = DashboardFilters(
        room_status_filters=room_statuses,
        financial_filters=financial_filters
    )
    return dashboard_service.get_landlord_dashboard(
        db=db,
        lodge_id=lodge_id,
        skip=skip,
        limit=limit,
        filter_by=all_filters,
        current_user=current_user
    )


@router.get(
    '/lease-info/{lease_id}',
    response_model=RoomLeaseInfo,
    summary="Get detailed room lease info",
    description="Retrieves detailed information about a specific lease including room details, tenant info, and financial breakdown.",
    response_description="Detailed room-lease-tenant-financial summary",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lease does not exist or user does not have access"},
    },
)
def get_room_lease_info(
    lease_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):

    return dashboard_service.get_dashboard_lease_info(
        db=db,
        lease_id=lease_id,
        current_user=current_user
    )