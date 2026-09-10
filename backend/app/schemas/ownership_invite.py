"""
Pydantic schemas for the ownership invitation domain.

This module contains schemas used to generate, inspect, and claim lodge ownership invites.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import OwnershipInviteStatus
from app.schemas.base_invite import BaseInviteCreate, BaseInviteResponse


class OwnershipInviteCreate(BaseInviteCreate):
    """
    Schema for generating an ownership claim invitation.
    """
    pass


class OwnershipInviteResponse(BaseInviteResponse):
    """
    Schema representing an ownership invitation record.
    """
    status: OwnershipInviteStatus = Field(validation_alias='computed_status', description="The current status of the invite.")
    claimed_by_user_id: Optional[int] = Field(None, description="The user ID of the landlord who claimed ownership.")


class OwnershipInviteDetail(BaseModel):
    """
    Schema for public preview of an ownership invitation.
    All fields are derived cleanly from model @property helpers.
    """
    invite_id: UUID = Field(validation_alias='id', description="The unique identifier for the invite.")
    lodge_name: str = Field(..., description="The name of the lodge.")
    target_phone_no: str = Field(..., description="The target landlord's phone number.")
    created_by_operator_name: str = Field(..., description="The full name of the operator who created the invite.")
    status: OwnershipInviteStatus = Field(validation_alias='computed_status', description="The computed status of the invite (ACTIVE, CONSUMED, EXPIRED).")
    claimed_by_user_id: Optional[int] = Field(None, description="The user ID of the landlord who claimed ownership.")
    expires_at: datetime = Field(..., description="Timestamp when the invite expires.")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

