"""
Pydantic schemas for the lodge operator domain.

This module contains schemas used to assign, revoke, and inspect lodge operators.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import OperatorStatus


class LodgeOperatorBase(BaseModel):
    """
    Base schema for operator actions on a lodge.
    """
    lodge_id: int = Field(..., description="The ID of the lodge.", examples=[1])
    operator_user_id: int = Field(..., description="The user ID of the operator.", examples=[42])


class AssignExistingOperatorCreate(LodgeOperatorBase):
    """
    Schema for assigning an existing operator user to a lodge.
    """
    pass






class LodgeOperatorResponse(BaseModel):
    """
    Schema representing a lodge operator junction record.
    """
    id: int = Field(..., description="Primary key of the junction record.", examples=[1])
    lodge_id: int = Field(..., description="The ID of the lodge.", examples=[1])
    operator_id: int = Field(..., description="The user ID of the operator.", examples=[42])
    status: OperatorStatus = Field(..., description="The status of the assignment.", examples=[OperatorStatus.ASSIGNED])
    assigned_at: datetime = Field(..., description="Timestamp when the operator was assigned.")
    revoked_at: Optional[datetime] = Field(None, description="Timestamp when the operator was revoked.")

    model_config = ConfigDict(from_attributes=True)
