"""
Pydantic schemas for the lodge domain.

This module contains schemas used to represent, create, and update lodges.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator, Field

from app.schemas.room import RoomResponse
from app.schemas.tenantprofile import TenantProfileResponse


class LodgeBase(BaseModel):
    """
    Base schema for a lodge.

    Attributes:
        name (str): The name of the lodge.
        address (str): The address of the lodge.
    """
    name: str = Field(..., description="The name of the lodge.", examples=["Sunrise Lodge"])
    address: str = Field(..., description="The address of the lodge.", examples=["123 Sunrise Ave"])

    @field_validator('name', 'address')
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip().lower()

class RoomGenerator(BaseModel):
    prefix: Optional[str] = Field(None, description="Optional prefix for room numbering e.g. 'A' or 'Rm'.", examples=["A"])
    start_number: int = Field(..., description="Starting number for the generated rooms.", examples=[1])

    end_number: int = Field(..., description="Ending number for the generated rooms.", examples=[20])
    default_rent: int = Field(..., description="Default rent amount in KOBO.", examples=[20000000])
    default_description: str = Field(..., description="Default description for the generated rooms.", examples=["Standard single room"])

class LodgeCreate(LodgeBase):
    room_generator: Optional[RoomGenerator] = Field(None, description="Optional configuration to generate rooms automatically.", examples=[None])

class LodgeInternal(LodgeBase):
    pass


class LodgeResponse(LodgeBase):
    id: int = Field(..., description="The unique identifier for the lodge.", examples=[1])
    landlord_id: Optional[int] = Field(None, description="The ID of the landlord owning this lodge (None if unclaimed).", examples=[1])
    created_by_user_id: Optional[int] = Field(None, description="The ID of the user who provisioned the lodge.", examples=[1])
    is_claimed: bool = Field(..., description="Whether the lodge has been claimed by a landlord.", examples=[True])
    created_at: datetime = Field(..., description="Timestamp when the lodge was created.", examples=["2026-07-04T06:05:02Z"])
    is_active: bool = Field(..., description="Whether the lodge is active.", examples=[True])


    model_config = {'from_attributes': True}



class LodgeUpdate(BaseModel):
    name: Optional[str] = Field(None, description="The name of the lodge.", examples=["Sunrise Lodge"])
    address: Optional[str] = Field(None, description="The address of the lodge.", examples=["123 Sunrise Ave"])

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.lower()
