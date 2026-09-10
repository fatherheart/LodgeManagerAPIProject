"""
Pydantic schemas for the lease domain.

This module contains schemas used to represent, create, and update lease agreements.
"""
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import date, datetime
from app.core.enums import LeaseStatus
from app.core.exceptions import RentAmtExceededError
from app.schemas.room import RoomGridSummary


class LeaseBase(BaseModel):
    """
    Base schema for a lease agreement.

    Attributes:
        tenant_id (int): The ID of the tenant.
        room_id (int): The ID of the leased room.
        agreed_rent_amt (int): The agreed rental amount.
        start_date (date): The start date of the lease.
        end_date (date): The end date of the lease.
    """
    tenant_id: int = Field(..., description="The ID of the tenant.", examples=[1])
    room_id: int = Field(..., description="The ID of the leased room.", examples=[1])
    agreed_rent_amt: int = Field(..., ge=0, description="The agreed ANNUAL rental amount in KOBO.", examples=[20000000])
    start_date: date = Field(..., description="The start date of the lease.", examples=["2026-01-01"])
    end_date: date = Field(..., description="The end date of the lease.", examples=["2026-12-31"])



class LeaseCreate(LeaseBase):
    total_amt_paid: int = Field(..., gt=0, description="The initial upfront payment in KOBO.", examples=[20000000])

    @model_validator(mode='after')
    def validate_lease_terms(self):
        if self.end_date <= self.start_date:
            raise ValueError("Lease end date must be after the start date.")
        if self.total_amt_paid > self.agreed_rent_amt:
            raise ValueError("Upfront payment cannot exceed agreed rent amount.")
        return self


class LeaseResponse(LeaseBase):
    id: int = Field(..., description="The unique identifier for the lease.", examples=[1])
    created_at : datetime = Field(..., description="Timestamp when the lease was created.", examples=["2026-07-04T06:05:02Z"])
    status: LeaseStatus = Field(validation_alias='computed_status', description="The current status of the lease.", examples=["active"])

    model_config = ConfigDict(from_attributes=True)


class LeaseUpdate(BaseModel):
    agreed_rent_amt: Optional[int]  = Field(None, ge=0, description="The agreed ANNUAL rental amount in KOBO.", examples=[20000000])
    end_date: Optional[date] = Field(None, description="The end date of the lease.", examples=["2026-12-31"])

class OccupiedRoomLeasesResponse(BaseModel):
    safe: list[RoomGridSummary] = Field(..., description="List of rooms with safe leases.", examples=[[]])
    expiring: list[RoomGridSummary] = Field(..., description="List of rooms with expiring leases.", examples=[[]])
    overdue: list[RoomGridSummary] = Field(..., description="List of rooms with overdue payments.", examples=[[]])
    pending_moveout: list[RoomGridSummary] = Field(..., description="List of rooms with pending leases.", examples=[[]])
    owing: list[RoomGridSummary] = Field(..., description="List of rooms with owing balances.", examples=[[]])

class LeaseHistoryResponse(LeaseResponse):
    tenant_name: str = Field(..., description="The name of the tenant.", examples=["John Doe"])
    room_no: str = Field(..., description="The room number.", examples=["A1"])



