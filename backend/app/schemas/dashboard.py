"""
Pydantic schemas for the dashboard domain.

This module contains schemas used to structure the data for the landlord's dashboard,
including financial summaries, entity counts, and room statuses.
"""
from datetime import date
from enum import Enum
from typing import Optional, Annotated

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import BadgeTexts, BadgeVariants, RoomStatus
from app.schemas.entity_count import EntityCountResponse
from app.schemas.financial import FinancialResponse
from app.schemas.lease import OccupiedRoomLeasesResponse, LeaseBase
from app.schemas.room import RoomGridSummary, RoomCreate, RoomBase


class LandlordDashboardStats(BaseModel):
    """
    Schema representing the complete dashboard statistics for a landlord.

    Attributes:
        financials (FinancialResponse): The financial summary.
        entity_counts (EntityCountResponse): The counts of different entities.
        occupied_rooms_lease (OccupiedRoomLeasesResponse): The lease details of occupied rooms.
        vacant_rooms (list[RoomGridSummary]): The list of vacant rooms.
        maintenance_rooms (list[RoomGridSummary]): The list of rooms under maintenance.
    """
    financials: FinancialResponse = Field(..., description="The financial summary.", examples=[{"potential_revenue": 5000000, "forecasted_revenue": 4500000, "expected_revenue": 4000000, "collected_revenue": 3500000, "unpaid_rent": 500000}])
    entity_counts: EntityCountResponse = Field(..., description="The counts of different entities.", examples=[{"total_rooms": 10, "total_tenants": 8, "room_status_counts": {"occupied": 8, "vacant": 2, "maintenance": 0}, "occupied_counts": {"safe": 8, "expiring": 0, "overdue": 0, "pending": 0, "owing": 0}, "occupancy_rate": 80}])
    occupied_rooms_lease: OccupiedRoomLeasesResponse = Field(..., description="The lease details of occupied rooms.", examples=[{"safe": [], "expiring": [], "overdue": [], "pending": [], "owing": []}])
    vacant_rooms: list[RoomGridSummary] = Field(..., description="The list of vacant rooms.", examples=[[]])
    maintenance_rooms: list[RoomGridSummary] = Field(..., description="The list of rooms under maintenance.", examples=[[]])

    model_config = ConfigDict(from_attributes=True)

class DashboardFilters(BaseModel):
    """
    Schema for filtering dashboard statistics.

    Attributes:
        room_status_filters (list[RoomStatus]): Filters for room statuses.
        financial_filters (list[BadgeTexts]): Filters for financial categories.
    """
    room_status_filters: list[RoomStatus] = Field(..., description="Filters for room statuses.", examples=[["vacant", "occupied"]])
    financial_filters: list[BadgeTexts] = Field(..., description="Filters for financial categories.", examples=[["Safe"]])

class RoomSummary(BaseModel):
    room_no: str = Field(..., description="The room number.", examples=["101"])
    description: str = Field(..., description="The description of the room.", examples=["Single room"])
    base_rent: int = Field(..., description="The base rent in KOBO.", examples=[20000000])
    status: str = Field(..., description="The status of the room.", examples=["vacant"])

class LeaseSummary(BaseModel):
    start_date: date = Field(..., description="The start date of the lease.", examples=["2026-01-01"])
    end_date: date = Field(..., description="The end date of the lease.", examples=["2026-12-31"])
    days_left: int = Field(..., description="The number of days left on the lease.", examples=[30])

class FinancialSummary(BaseModel):
    agreed_rent: int = Field(..., description="The agreed rent in KOBO.", examples=[20000000])
    total_paid: int = Field(..., description="The total amount paid in KOBO.", examples=[15000000])
    remaining_balance: int = Field(..., description="The remaining balance in KOBO.", examples=[5000000])

class TenantSummary(BaseModel):
    name: str = Field(..., description="The tenant's name.", examples=["John Doe"])
    phone: str = Field(..., description="The tenant's phone number.", examples=["+2348012345678"])

class RoomLeaseBase(BaseModel):
    room: RoomSummary = Field(..., description="The room summary.", examples=[{"room_no": "101", "description": "Single room", "base_rent": 20000000, "status": "vacant"}])
    lease: LeaseSummary = Field(..., description="The lease summary.", examples=[{"start_date": "2026-01-01", "end_date": "2026-12-31", "days_left": 30}])
    finance: FinancialSummary = Field(..., description="The financial summary.", examples=[{"agreed_rent": 20000000, "total_paid": 15000000, "remaining_balance": 5000000}])
    badge_text: BadgeTexts = Field(..., description="The text to display on the badge.", examples=["Safe"])
    badge_variant: BadgeVariants = Field(..., description="The visual variant of the badge.", examples=["success"])

class RoomLeaseInfo(RoomLeaseBase):
    tenant: TenantSummary = Field(..., description="The tenant summary.", examples=[{"name": "John Doe", "phone": "+2348012345678"}])


class TenantDashboardStats(RoomLeaseBase):
    pass


