"""
SQLAlchemy models for the lodge domain.

This module contains the Lodge model which represents a building or property
owned by a landlord that contains rooms for rent.
"""
from datetime import datetime

from sqlalchemy.sql import func
from sqlalchemy import Integer, String, ForeignKey, DateTime, Boolean
from app.db.session import Base
from sqlalchemy.orm  import relationship,mapped_column, Mapped

from typing import TYPE_CHECKING, Optional

from app.models.invitation import Invite

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.room import Room
    from app.models.tenantprofile import TenantProfile
    from app.models.lodge_operator import LodgeOperator
    from app.models.ownership_invite import OwnershipInvite
    from app.models.operator_invite import OperatorInvite

class Lodge(Base):
    """
    Represents a lodge or property containing rentable rooms.

    Attributes:
        id (int): Primary key.
        name (str): The name of the lodge.
        address (str): The physical address of the lodge.
        landlord_id (int | None): Foreign key to the user (landlord) who owns the lodge (None if unclaimed).
        created_by_user_id (int): Foreign key to the user who provisioned the lodge.
        created_at (datetime): Timestamp when the lodge was created.
        is_active (bool): Indicates if the lodge is currently active.
        owner (User): Relationship to the user who owns the lodge.
        creator (User): Relationship to the user who created the lodge.
        rooms (list[Room]): Relationship to the rooms within the lodge.
        tenantprofiles (list[TenantProfile]): Relationship to the tenant profiles associated with this lodge.
        operators (list[LodgeOperator]): Relationship to assigned operators.
        ownership_invites (list[OwnershipInvite]): Relationship to ownership claim invites.
        operator_invites (list[OperatorInvite]): Relationship to operator assignment invites.
    """
    __tablename__ = 'lodges'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    address: Mapped[str] = mapped_column(nullable=False)
    landlord_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    owner: Mapped[Optional["User"]] = relationship(back_populates='lodges', foreign_keys=[landlord_id])
    creator: Mapped[Optional["User"]] = relationship(foreign_keys=[created_by_user_id])

    rooms: Mapped[list["Room"]] = relationship(back_populates='lodge', cascade='all, delete-orphan')
    tenantprofiles: Mapped[list["TenantProfile"]] = relationship(back_populates='lodge', cascade='all, delete-orphan')
    operators: Mapped[list["LodgeOperator"]] = relationship(back_populates='lodge', cascade='all, delete-orphan')
    ownership_invites: Mapped[list["OwnershipInvite"]] = relationship(back_populates='lodge', cascade='all, delete-orphan')
    operator_invites: Mapped[list["OperatorInvite"]] = relationship(back_populates='lodge', cascade='all, delete-orphan')

    @property
    def is_claimed(self) -> bool:
        return self.landlord_id is not None

    def is_owned_by(self, user_id: int) -> bool:
        """Check if this lodge is claimed and legally owned by a specific landlord."""
        return self.is_claimed and self.landlord_id == user_id



