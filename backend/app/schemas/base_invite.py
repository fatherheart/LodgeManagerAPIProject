"""
Pydantic schemas for the invitation domain.

This module contains base schemas for invitations across domains (Tenant, Ownership, Operator).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BaseInviteCreate(BaseModel):
    """
    Base schema for creating a phone-locked invitation for a lodge.
    Shared by Ownership and Operator invitations.
    """
    lodge_id: int = Field(..., description="The ID of the lodge.", examples=[1])
    target_phone_no: str = Field(..., description="The target phone number locked to this invite.", examples=["+2348012345678"])


class BaseInviteResponse(BaseModel):
    """
    Base schema representing a generated invitation.
    """
    id: UUID = Field(..., description="The unique identifier for the invite.")
    lodge_id: int = Field(..., description="The ID of the lodge.")
    created_by_user_id: int = Field(..., description="The user ID of who generated the invite.")
    target_phone_no: str = Field(..., description="The target phone number.")
    expires_at: datetime = Field(..., description="Timestamp when the invite expires.")
    created_at: datetime = Field(..., description="Timestamp when the invite was generated.")

    model_config = ConfigDict(from_attributes=True)
