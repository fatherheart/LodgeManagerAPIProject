from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.core.enums import InviteStatus


class InviteCreate(BaseModel):
    room_id: int = Field(..., description="The ID of the room to invite for.", examples=[1])
    expires_at: datetime = Field(..., description="The expiration date and time of the invite.", examples=["2026-07-04T06:05:02Z"])


class InviteResponse(BaseModel):
    id: UUID = Field(..., description="The unique identifier for the invite.", examples=["123e4567-e89b-12d3-a456-426614174000"])
    lodge_id: int = Field(..., description="The ID of the lodge.", examples=[1])
    room_id: int = Field(..., description="The ID of the room.", examples=[1])
    room_no: str = Field(..., description="The room number.", examples=["Room 101"])
    status: InviteStatus = Field(..., description="The current status of the invite.", examples=["Sent"])
    created_at: datetime = Field(..., description="Timestamp when the invite was created.", examples=["2026-07-04T06:05:02Z"])
    expires_at: datetime = Field(..., description="The expiration date and time of the invite.", examples=["2026-07-04T06:05:02Z"])
    is_expired: bool = Field(..., description="Whether the invite has expired.", examples=[False])

    model_config = ConfigDict(from_attributes=True)


class InviteDetail(BaseModel):
    id: UUID = Field(..., description="The unique identifier for the invite.", examples=["123e4567-e89b-12d3-a456-426614174000"])
    lodge_name: str = Field(..., description="The name of the lodge.", examples=["Sunrise Lodge"])
    room_no: str = Field(..., description="The room number.", examples=["Room 101"])
    is_expired: bool = Field(..., description="Whether the invite has expired.", examples=[False])

    model_config = ConfigDict(from_attributes=True)

