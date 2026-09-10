"""
SQLAlchemy models for the invitation domain.
This module contains the database model for tracking tenant invitations sent by landlords.
"""
from app.core.enums import InviteStatus
from app.db.session import Base
from datetime import date, datetime, timezone
from sqlalchemy import ForeignKey, Enum, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import TYPE_CHECKING, Optional
import uuid

if TYPE_CHECKING:
    from app.models.lodge import Lodge
    from app.models.room import Room
    from app.models.tenantprofile import TenantProfile

class Invite(Base):
    """
    SQLAlchemy model representing a tenant invitation.
    
    Attributes:
        id: Primary key UUID for the invitation.
        room_id: Foreign key referencing the room the invite is for.
        accepted_by_tenant_id: Foreign key referencing the tenant who redeemed the invite.
        created_at: Timestamp when the invite was generated.
        expires_at: Timestamp when the invite expires.
        status: The current status of the invite (SENT, ACCEPTED, EXPIRED).
    """
    __tablename__ = 'invites'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    accepted_by_tenant_id: Mapped[Optional[int]] = mapped_column(ForeignKey('tenant_profiles.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[InviteStatus] = mapped_column(default=InviteStatus.SENT, nullable=False)

    room: Mapped["Room"] = relationship(back_populates='invites')
    accepted_by_tenant: Mapped[Optional["TenantProfile"]] = relationship(back_populates='invite')

    @property
    def lodge(self):
        return self.room.lodge if self.room else None

    @property
    def lodge_id(self):
        return self.room.lodge_id if self.room else None

    @property
    def lodge_name(self):
        return self.room.lodge.name if self.room and self.room.lodge else 'N/A'

    @property
    def room_no(self):
        return self.room.room_no if self.room else 'N/A'

    @property
    def is_expired(self):
        curr_time = datetime.now(timezone.utc).replace(tzinfo=None)
        return curr_time > self.expires_at