"""
Module providing CRUD operations for the OwnershipInvite domain.

Manages creation, retrieval, cancellation, and consumption of lodge
ownership invitations issued by operators to prospective landlords.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import OwnershipInviteStatus
from app.models.ownership_invite import OwnershipInvite


class CRUDOwnershipInvite:
    def __init__(self, model=OwnershipInvite):
        self.model = model

    def get_active_invite_for_lodge(self, db: Session, lodge_id: int) -> Optional[OwnershipInvite]:
        """
        Return the current active (NULL status, not expired) invite for a lodge.
        NULL status is the sentinel value for ACTIVE — no stored value means no action taken yet.
        """
        curr_time = datetime.utcnow()
        stmt = select(self.model).where(
            self.model.lodge_id == lodge_id,
            self.model.status.is_(None),
            self.model.expires_at > curr_time
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, db: Session, invite_id: UUID) -> Optional[OwnershipInvite]:
        """
        Fetch a specific ownership invite by UUID with eager-loaded relationships.
        """
        stmt = select(self.model).where(
            self.model.id == invite_id
        ).options(
            joinedload(self.model.lodge),
            joinedload(self.model.created_by_operator)
        )
        return db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        db: Session,
        lodge_id: int,
        created_by_user_id: int,
        target_phone_no: str,
        expires_at: datetime
    ) -> OwnershipInvite:
        """
        Persist a new ownership invite. Status is left NULL (ACTIVE by convention).
        """
        invite = self.model(
            lodge_id=lodge_id,
            created_by_user_id=created_by_user_id,
            target_phone_no=target_phone_no,
            expires_at=expires_at
        )
        db.add(invite)
        db.commit()
        db.refresh(invite)
        return invite

    def cancel(self, db: Session, invite: OwnershipInvite) -> OwnershipInvite:
        """
        Mark a pending invite as CANCELLED. Unblocks the operator to re-issue immediately.
        """
        invite.status = OwnershipInviteStatus.CANCELLED
        db.commit()
        db.refresh(invite)
        return invite

    def consume(self, db: Session, invite: OwnershipInvite, claimed_by_user_id: int):
        """
        Atomically transfer lodge ownership and mark the invite as CONSUMED.
        Both the lodge.landlord_id update and the invite status change are committed together.
        Returns the claimed Lodge.
        """
        invite.status = OwnershipInviteStatus.CONSUMED
        invite.claimed_by_user_id = claimed_by_user_id
        invite.lodge.landlord_id = claimed_by_user_id

        try:
            db.commit()
            db.refresh(invite.lodge)
            db.refresh(invite)
        except Exception:
            db.rollback()
            raise

        return invite.lodge



crud_ownership_invite = CRUDOwnershipInvite()
