"""
Pydantic schemas for the room domain.

This module contains schemas used to represent, create, and update rooms,
as well as summarizing room statuses for dashboards.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Union
from app.core.enums import BadgeTexts, BadgeVariants
from app.core.enums import  RoomStatus
from datetime import datetime


class RoomBase(BaseModel):
    """
    Base schema for a room.

    Attributes:
        room_no (str): The room number or identifier.
        description (Optional[str]): The description of the room.
        base_rent_price (int): The base rental price.
        status (RoomStatus): The current status of the room.
    """
    room_no: str = Field(..., description="The room number or identifier.", examples=["A1", "101"])
    description: Optional[str] = Field(None, description="The description of the room.", examples=["Spacious self-contain"])
    base_rent_price: int = Field(default=200000, ge=0, description="The base rental price in KOBO.", examples=[20000000])


    @field_validator('room_no', 'description')
    @classmethod
    def clean_strings(cls, value: str) -> Optional[str]:
        return value.strip().lower() if value else value


class RoomCreate(RoomBase):
    lodge_id: int = Field(..., description="The ID of the lodge this room belongs to.", examples=[1])
    pass


class RoomResponse(RoomCreate):
    id: int = Field(..., description="The unique identifier for the room.", examples=[1])
    status: RoomStatus = Field(..., description="The current status of the room.",
                               examples=["vacant"], validation_alias='computed_status')
    created_at: datetime = Field(..., description="Timestamp when the room was created.", examples=["2026-07-04T06:05:02Z"])
    
    has_active_invite: bool = Field(False, description="Whether the room has an active invite.")
    pending_applicant: Optional['PendingApplicantSummary'] = Field(None, description="The pending applicant details if any.")

    model_config = ConfigDict(from_attributes=True)


class PendingApplicantSummary(BaseModel):
    tenant_id: int = Field(..., description="The ID of the pending tenant.", examples=[1])
    first_name: str = Field(..., description="Tenant's first name.", examples=["John"])
    last_name: str = Field(..., description="Tenant's last name.", examples=["Doe"])
    phone_no: str = Field(..., description="Tenant's phone number.", examples=["+2348012345678"])

    model_config = ConfigDict(from_attributes=True)


class RoomStatusCounts(BaseModel):
    occupied: int = Field(..., description="Number of occupied rooms.", examples=[10])
    vacant: int = Field(..., description="Number of vacant rooms.", examples=[5])
    maintenance: int = Field(..., description="Number of rooms under maintenance.", examples=[2])

    model_config = ConfigDict(from_attributes=True)


class RoomUpdate(BaseModel):
    room_no: Optional[str] = Field(None, description="The room number or identifier.", examples=["A1", "101"])
    description: Optional[str] = Field(None, description="The description of the room.", examples=["Spacious self-contain"])
    base_rent_price: Optional[int] = Field(None, ge=0, description="The base rental price in KOBO.", examples=[20000000])
    status: Optional[RoomStatus] = Field(None, description="The current status of the room.",
                                         examples=["Maintenance"])


class RoomGridSummary(BaseModel):
    lease_id: Optional[int] = Field(None, description="The ID of the active lease, if any.", examples=[1])
    room_id: int = Field(..., description="The ID of the room.", examples=[1])
    room_no: str = Field(..., description="The room number.", examples=["101"])
    badge_text: Union[BadgeTexts, RoomStatus] = Field(..., description="The text to display on the badge.", examples=["Safe"])
    badge_variant: BadgeVariants = Field(..., description="The visual variant of the badge.", examples=["success"])
    main_display_text: str = Field(..., description="Main text displayed on the grid card.", examples=["Donald"])
    sub_display_text: str = Field(..., description="Sub text displayed on the grid card.", examples=["91 days left"])
    is_owing: bool = Field(False, description="Whether the room currently has an owing balance.", examples=[False])

class BulkRoomUpdate(BaseModel):
    room_ids: list[int] = Field(..., description="List of room IDs to update.", examples=[[1, 2, 3]])
    base_rent: int = Field(..., ge=0, description="The new base rent amount in KOBO.", examples=[25000000])


if __name__ == '__main__':

    summary_dict = {
        'lease_id': 1,
        'room_no': '29',
        'badge_text': BadgeTexts.SAFE,
        'badge_variant': BadgeVariants.SUCCESS,
        'main_display_text': 'Donald',
        'sub_display_text': '91 days left'
    }

    print(RoomGridSummary.model_validate(summary_dict).model_dump_json(indent=4))

