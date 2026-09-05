"""
Pydantic schemas for the operator invitation domain.

This module contains schemas used to invite and register new caretakers/operators.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import OperatorInviteStatus
from app.schemas.user import UserCreate
from app.schemas.base_invite import BaseInviteCreate, BaseInviteResponse


class OperatorInviteCreate(BaseInviteCreate):
    """
    Schema for generating an operator assignment invitation.
    """
    pass


class OperatorInviteResponse(BaseInviteResponse):
    """
    Schema representing an operator invitation record.
    """
    status: OperatorInviteStatus = Field(..., description="The current status of the invite.")
    accepted_by_user_id: Optional[int] = Field(None, description="The user ID of the operator who accepted.")


class OperatorInviteDetail(BaseModel):
    """
    Schema for public preview of an operator invitation.
    All fields are derived cleanly from model @property helpers.
    """
    invite_id: UUID = Field(..., description="The unique identifier for the invite.")
    lodge_name: str = Field(..., description="The name of the lodge.")
    target_phone_no: str = Field(..., description="The intended operator's phone number.")
    created_by_landlord_name: str = Field(..., description="The full name of the landlord who sent the invite.")
    status: OperatorInviteStatus = Field(..., description="The computed status of the invite (ACTIVE, ACCEPTED, EXPIRED).")
    expires_at: datetime = Field(..., description="Timestamp when the invite expires.")

    model_config = ConfigDict(from_attributes=True)


class OperatorInviteRegistrationCreate(BaseModel):
    """
    Schema for registering a new operator via an invitation.
    """
    user_info: UserCreate = Field(..., description="The operator user's registration details.")
    invite_id: UUID = Field(..., description="The assignment invitation token.")
