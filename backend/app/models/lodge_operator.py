"""
SQLAlchemy model for the lodge operator junction domain.

This module contains the LodgeOperator model which represents the many-to-many
relationship between lodges and their assigned caretakers/operators.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OperatorStatus
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.lodge import Lodge
    from app.models.user import User


class LodgeOperator(Base):
    """
    SQLAlchemy model representing an operator assignment to a lodge.

    Attributes:
        id: Primary key.
        lodge_id: Foreign key to the lodge.
        operator_id: Foreign key to the operator user.
        status: The assignment status (ASSIGNED, REVOKED).
        assigned_at: Timestamp when the operator was assigned.
        revoked_at: Timestamp when the operator was revoked (if applicable).
    """
    __tablename__ = 'lodge_operators'
    __table_args__ = (
        UniqueConstraint('lodge_id', 'operator_id', name='uq_lodge_operator'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lodge_id: Mapped[int] = mapped_column(ForeignKey('lodges.id', ondelete='CASCADE'), nullable=False)
    operator_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status: Mapped[OperatorStatus] = mapped_column(
        SQLEnum(OperatorStatus),
        default=OperatorStatus.ASSIGNED,
        nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    lodge: Mapped["Lodge"] = relationship(back_populates='operators')
    operator: Mapped["User"] = relationship(back_populates='operated_lodges')
