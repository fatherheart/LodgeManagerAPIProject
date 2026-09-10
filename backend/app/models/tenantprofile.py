"""
SQLAlchemy models for the tenant profile domain.

This module contains the TenantProfile model which represents the details
and status of a tenant living in a lodge.
"""
from pygments.lexer import default

from app.core.enums import TenantType, StudentLevel, TenantStatus
from app.db.session import  Base
from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import TYPE_CHECKING, Optional
import uuid

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.lodge import Lodge
    from app.models.lease import Lease
    from app.models.invitation import Invite


class TenantProfile(Base):
    """
    Represents a tenant's profile and their associated details.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to the associated user account.
        lodge_id (int): Foreign key to the lodge where the tenant resides.
        invite_id (UUID | None): Foreign key to the invitation used during onboarding.
        tenant_type (TenantType): The type of tenant (e.g., STUDENT, PROFESSIONAL).
        emergency_contact_name (str): Name of the emergency contact.
        emergency_contact_phone_no (str): Phone number of the emergency contact.
        level (StudentLevel | None): The academic level if the tenant is a student.
        department (str | None): The academic department if the tenant is a student.
        reg_no (str | None): The registration number if the tenant is a student.
        user (User): Relationship to the associated user account.
        lodge (Lodge): Relationship to the associated lodge.
        leases (Lease): Relationship to the tenant's leases.
        invite (Invite): Relationship to the onboarding invitation.
    """
    __tablename__ = 'tenant_profiles'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    lodge_id: Mapped[int] = mapped_column(ForeignKey('lodges.id', ondelete='CASCADE'), nullable=False)
    tenant_type: Mapped[TenantType] = mapped_column(Enum(TenantType), nullable=False, default=TenantType.STUDENT)
    emergency_contact_name: Mapped[str] = mapped_column(String(20), nullable=False,  index=True)
    emergency_contact_phone_no: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[TenantStatus] = mapped_column(Enum(TenantStatus), default=TenantStatus.PENDING)
    level: Mapped[StudentLevel | None] = mapped_column(Enum(StudentLevel), nullable=True)
    department: Mapped[str | None] = mapped_column(nullable=True)
    reg_no: Mapped[str | None] = mapped_column(nullable=True)
    user: Mapped["User"] = relationship(back_populates='tenant_profile', cascade='all, delete-orphan', single_parent=True)
    lodge: Mapped["Lodge"] = relationship(back_populates='tenantprofiles')
    leases: Mapped[list["Lease"]] = relationship(back_populates='tenant')
    invite: Mapped[Optional["Invite"]] = relationship(back_populates='accepted_by_tenant', uselist=False)

    @property
    def is_active(self):
        return self.user.is_active if self.user else True

    @property
    def created_at(self):
        return self.user.created_at if self.user else None

    @property
    def role(self):
        return self.user.role if self.user else None

    @property
    def is_onboarding(self) -> bool:
        return len(self.leases) == 0