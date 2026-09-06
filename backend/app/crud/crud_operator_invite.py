"""
Module providing CRUD operations for the OperatorInvite domain.

Manages creation, retrieval, cancellation, and acceptance of lodge
operator/caretaker invitations issued by landlords.
Inherits from CRUDBase for standard model operations.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import OperatorInviteStatus
from app.crud.base_crud import CRUDBase
from app.models.operator_invite import OperatorInvite
from app.schemas.operator_invite import OperatorInviteCreate


class CRUDOperatorInvite(CRUDBase[OperatorInvite, OperatorInviteCreate, Any]):
    def __init__(self, model=OperatorInvite):
        super().__init__(model)

    def get_active_invite_for_phone_and_lodge(
        self, db: Session, lodge_id: int, target_phone_no: str
    ) -> Optional[OperatorInvite]:
        """
        Return the current active (NULL status, not expired) invite for a target phone and lodge.
        NULL status is the sentinel value for ACTIVE.
        """
        curr_time = datetime.utcnow()
        stmt = select(self.model).where(
            self.model.lodge_id == lodge_id,
            self.model.target_phone_no == target_phone_no,
            self.model.status.is_(None),
            self.model.expires_at > curr_time
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, db: Session, invite_id: UUID) -> Optional[OperatorInvite]:
        """
        Fetch a specific operator invite by UUID with eager-loaded relationships.
        """
        stmt = select(self.model).where(
            self.model.id == invite_id
        ).options(
            joinedload(self.model.lodge),
            joinedload(self.model.created_by_landlord)
        )
        return db.execute(stmt).scalar_one_or_none()

    def create_invite(
        self,
        db: Session,
        lodge_id: int,
        created_by_user_id: int,
        target_phone_no: str,
        expires_at: datetime
    ) -> OperatorInvite:
        """
        Persist a new operator invite with status NULL (ACTIVE).
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

    def cancel(self, db: Session, invite: OperatorInvite) -> OperatorInvite:
        """
        Mark a pending operator invite as CANCELLED.
        """
        invite.status = OperatorInviteStatus.CANCELLED
        db.commit()
        db.refresh(invite)
        return invite

    def accept(self, db: Session, invite: OperatorInvite, accepted_by_user_id: int) -> OperatorInvite:
        """
        Atomically persist the acceptance of an operator invite.
        Marks status as ACCEPTED and sets accepted_by_user_id.
        Any associated LodgeOperator assignment already appended to
        the session or relationship is committed in this same transaction.
        """
        invite.status = OperatorInviteStatus.ACCEPTED
        invite.accepted_by_user_id = accepted_by_user_id

        try:
            db.commit()
            db.refresh(invite)
        except Exception:
            db.rollback()
            raise

        return invite


crud_operator_invite = CRUDOperatorInvite()
