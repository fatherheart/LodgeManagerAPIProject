"""
Pydantic schemas for entity counting.

This module contains schemas used to represent the counts of different
entities in the system, such as rooms and tenants.
"""
from pydantic import BaseModel, ConfigDict, ValidationError, Field

from app.schemas.room import RoomStatusCounts


class EntityCountResponse(BaseModel):
    """
    Schema representing the count of various entities in the system.

    Attributes:
        total_rooms (int): The total number of rooms.
        total_tenants (int): The total number of tenants.
        room_status_counts (RoomStatusCounts): The counts of rooms by status.
        occupied_counts (OccupiedCounts): The counts of occupied rooms by state.
    """
    total_rooms: int = Field(..., description="The total number of rooms.", examples=[40])
    total_tenants: int = Field(..., description="The total number of tenants.", examples=[35])
    room_status_counts : RoomStatusCounts = Field(..., description="The counts of rooms by status.", examples=[{"occupied": 30, "vacant": 6, "maintenance": 4}])
    occupied_counts: OccupiedCounts = Field(..., description="The counts of occupied rooms by state.", examples=[{"safe": 10, "expiring": 10, "overdue": 2, "pending": 0, "owing": 8}])
    occupancy_rate: int = Field(..., description="The occupancy rate percentage.", examples=[85])

    model_config = ConfigDict(from_attributes=True)


class OccupiedCounts(BaseModel):
    """
    Schema representing the counts of occupied rooms categorized by their lease state.

    Attributes:
        safe (int): Number of rooms with safe leases.
        expiring (int): Number of rooms with expiring leases.
        overdue (int): Number of rooms with overdue payments.
        owing (int): Number of rooms with owing balances.
    """
    safe: int = Field(..., description="Number of rooms with safe leases.", examples=[10])
    expiring: int = Field(..., description="Number of rooms with expiring leases.", examples=[5])
    overdue: int = Field(..., description="Number of rooms with overdue payments.", examples=[2])
    pending_moveout: int = Field(..., description="Number of rooms with move_out request on their leases", examples=[1])
    owing: int = Field(..., description="Number of rooms with owing balances.", examples=[3])


