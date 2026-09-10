"""
Pydantic schemas for the tenant profile domain.

This module contains schemas used to represent, create, and update tenant profiles.
"""
from datetime import datetime, date
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator, ConfigDict, Field

from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.enums import TenantType, StudentLevel, TenantStatus


class TenantBase(BaseModel):
    """
    Base schema for a tenant profile.

    Attributes:
        tenant_type (TenantType): The type of tenant.
        emergency_contact_name (str): The name of the emergency contact.
        emergency_contact_phone_no (str): The phone number of the emergency contact.
        level (Optional[StudentLevel]): The academic level if the tenant is a student.
        reg_no (Optional[int]): The registration number.
        department (Optional[str]): The academic department.
    """
    tenant_type: TenantType = Field(..., description="The type of tenant.", examples=["student"])
    emergency_contact_name: str = Field(..., description="The name of the emergency contact.", examples=["Jane Doe"])
    emergency_contact_phone_no: str = Field(..., description="The phone number of the emergency contact.", examples=["+2348012345678"])
    level: Optional[StudentLevel] = Field(None, description="The academic level if the tenant is a student.", examples=["100L"])
    reg_no: Optional[int] = Field(None, description="The registration number.", examples=[123456])
    department: Optional[str] = Field(None, description="The academic department.", examples=["Computer Science"])

    @field_validator('emergency_contact_name', 'emergency_contact_phone_no',
                     mode='before')
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip().lower()


class TenantProfileCreate(BaseModel):
    invite_id: UUID = Field(..., description="The UUID of the invitation used to create this profile.", examples=["123e4567-e89b-12d3-a456-426614174000"])
    user_info: UserCreate = Field(..., description="The user information for the new tenant.", examples=[{"first_name": "John", "last_name": "Doe", "email": "john@example.com", "phone_no": "+2348012345678", "password": "securepassword"}])
    tenant_info: TenantBase = Field(..., description="The tenant profile information.", examples=[{"tenant_type": "student", "emergency_contact_name": "Jane Doe", "emergency_contact_phone_no": "+2348012345678"}])


class TenantInfoUpdate(BaseModel):
    tenant_type: Optional[TenantType] = Field(None, description="The type of tenant.", examples=["student"])
    emergency_contact_name: Optional[str] = Field(None, description="The name of the emergency contact.", examples=["Jane Doe"])
    emergency_contact_phone_no: Optional[str] = Field(None, description="The phone number of the emergency contact.", examples=["+2348012345678"])
    level: Optional[StudentLevel] = Field(None, description="The academic level if the tenant is a student.", examples=["100L"])
    reg_no: Optional[int] = Field(None, description="The registration number.", examples=[123456])
    department: Optional[str] = Field(None, description="The academic department.", examples=["Computer Science"])
 
class TenantStatusUpdate(BaseModel):
    status: Optional[TenantStatus] = Field(None, description="The status of the tenant.", examples=["active"])


class TenantApprovalCreate(BaseModel):
    start_date: date = Field(..., description="The start date of the lease.", examples=["2026-01-01"])
    end_date: date = Field(..., description="The end date of the lease.", examples=["2026-12-31"])
    agreed_rent_amt: int = Field(..., ge=0, description="The agreed ANNUAL rental amount in KOBO.", examples=[20000000])
    total_amt_paid: int = Field(..., gt=0, description="The initial upfront payment in KOBO.", examples=[20000000])

    @model_validator(mode='after')
    def validate_lease_terms(self):
        if self.end_date <= self.start_date:
            raise ValueError("Lease end date must be after the start date.")
        if self.total_amt_paid > self.agreed_rent_amt:
            raise ValueError("Upfront payment cannot exceed agreed rent amount.")
        return self


class TenantProfileResponse(TenantBase):
    id: int = Field(..., description="The unique identifier for the tenant profile.", examples=[1])
    user_id: int = Field(..., description="The ID of the user associated with this profile.", examples=[1])
    created_at: datetime = Field(..., description="Timestamp when the profile was created.", examples=["2026-07-04T06:05:02Z"])
    status: TenantStatus = Field(..., description="The status of the tenant.", examples=["active"])
    is_active: bool = Field(..., description="Whether the tenant is active.", examples=[True])
    is_onboarding: bool = Field(..., description="Whether the tenant is currently in the onboarding process.", examples=[False])
    user: UserResponse = Field(..., description="The user information associated with this profile.", examples=[{"first_name": "John", "last_name": "Doe", "email": "john@example.com", "phone_no": "+2348012345678", "id": 1, "is_active": True, "created_at": "2026-07-04T06:05:02Z", "role": "TENANT"}])

    model_config = ConfigDict(from_attributes=True)


class TenantProfileUpdate(BaseModel):
    user_info: Optional[UserUpdate] = Field(None, description="The updated user information.", examples=[{"first_name": "Johnny"}])
    tenant_info: Optional[TenantInfoUpdate] = Field(None, description="The updated tenant information.", examples=[{"department": "Mathematics"}])


