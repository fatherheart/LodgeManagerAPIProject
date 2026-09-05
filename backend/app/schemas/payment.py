"""
Pydantic schemas for the payment domain.

This module contains schemas used to represent, create, and update payment records.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

from datetime import datetime


class PaymentBase(BaseModel):
    """
    Base schema for a payment.

    Attributes:
        amount_paid (int): The amount paid.
        lease_id (int): The ID of the lease this payment is for.
    """
    amount_paid: int = Field(..., gt=0, description="The amount paid in KOBO.", examples=[5000000])
    lease_id: int = Field(..., description="The ID of the lease this payment is for.", examples=[1])

class PaymentCreate(PaymentBase):
    payment_date: Optional[datetime] = Field(None, description="The date the payment was made.", examples=["2026-07-04T06:05:02Z"])

class PaymentResponse(PaymentBase):
    id: int = Field(..., description="The unique identifier for the payment.", examples=[1])
    payment_date: datetime = Field(..., description="The date the payment was made.", examples=["2026-07-04T06:05:02Z"])

    model_config = ConfigDict(from_attributes=True)