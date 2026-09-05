"""
SQLAlchemy models for the room domain.

This module contains the Room model which represents a specific room
within a lodge that can be leased to a tenant. It also includes data
classes for filtering rooms.
"""
from dataclasses import dataclass, field
from datetime import datetime,date
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import func
from app.db.session import Base
from sqlalchemy import String, Enum, ForeignKey, DateTime
from app.core.enums import RoomStatus, LeaseStatus

from typing import TYPE_CHECKING

from app.schemas.room import RoomGridSummary

if TYPE_CHECKING:
    from app.models.lodge import Lodge
    from app.models.lease import Lease
    from app.models.invitation import Invite


class Room(Base):
    """
    Represents a rentable room within a lodge.

    Attributes:
        id (int): Primary key.
        lodge_id (int): Foreign key to the lodge containing this room.
        room_no (str): The room number or identifier.
        description (str): A description of the room.
        base_rent_price (int): The base rental price for the room.
        status (RoomStatus): The current status of the room (e.g., VACANT, OCCUPIED).
        created_at (datetime): Timestamp when the room was created.
        leases (Lease): Relationship to the leases associated with this room.
        lodge (Lodge): Relationship to the lodge containing this room.
        invites (list[Invite]): Relationship to invitations sent for this room.
    """
    __tablename__ = 'rooms'

    id: Mapped[int] = mapped_column(primary_key=True)
    lodge_id: Mapped[int] = mapped_column(ForeignKey('lodges.id', ondelete='CASCADE'))
    room_no: Mapped[str] = mapped_column(index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300))
    base_rent_price: Mapped[int] = mapped_column(nullable=False, default=200000)
    status: Mapped["RoomStatus"] = mapped_column(Enum(RoomStatus), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    leases: Mapped[list["Lease"]] = relationship( back_populates='room')
    lodge: Mapped["Lodge"] = relationship( back_populates='rooms')
    invites: Mapped[list["Invite"]] = relationship(back_populates='room', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint(
            'room_no',
            'lodge_id',
            name='lodge_room_uc'
        ),)

    @property
    def computed_status(self) -> RoomStatus:
        if self.status == RoomStatus.MAINTENANCE:
            return RoomStatus.MAINTENANCE

        has_active_lease = any(
            (lease.status is None or lease.status == LeaseStatus.PENDING_TERMINATION)
            for lease in self.leases
        )

        return RoomStatus.OCCUPIED if has_active_lease else RoomStatus.VACANT

    @property
    def is_occupied(self) -> bool:
        """Check if the room is currently occupied by an active tenant lease."""
        return self.computed_status == RoomStatus.OCCUPIED

    @property
    def is_vacant(self) -> bool:
        """Check if the room is vacant and ready for leasing."""
        return self.computed_status == RoomStatus.VACANT

    @property
    def is_maintenance(self) -> bool:
        """Check if the room is under maintenance."""
        return self.computed_status == RoomStatus.MAINTENANCE



@dataclass
class RoomFilter:
    """
    Data class for filtering rooms by their status or condition.

    Attributes:
        safe (list[RoomGridSummary]): Rooms that are in a safe state.
        expiring (list[RoomGridSummary]): Rooms with leases expiring soon.
        overdue (list[RoomGridSummary]): Rooms with overdue payments.
        owing (list[RoomGridSummary]): Rooms with outstanding balances.
        vacant (list[RoomGridSummary]): Rooms that are currently vacant.
        maintenance (list[RoomGridSummary]): Rooms requiring maintenance.
    """
    safe: list[RoomGridSummary] = field(default_factory=list)
    expiring:  list[RoomGridSummary] = field(default_factory=list)
    overdue: list[RoomGridSummary] = field(default_factory=list)
    owing: list[RoomGridSummary] = field(default_factory=list)
    vacant: list[RoomGridSummary] = field(default_factory=list)
    maintenance: list[RoomGridSummary] = field(default_factory=list)
