"""
Module providing CRUD operations for the LodgeOperator junction domain.

This module manages operator assignments to lodges.
"""
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload

from app.core.enums import OperatorStatus
from app.models.lodge_operator import LodgeOperator
from app.models.lodge import Lodge


class CRUDLodgeOperator:
    def __init__(self, model=LodgeOperator):
        self.model = model

    def get_active_assignment(self, db: Session, lodge_id: int, operator_id: int) -> Optional[LodgeOperator]:
        """
        Check if an operator is currently actively assigned to a specific lodge.
        """
        stmt = select(self.model).where(
            self.model.lodge_id == lodge_id,
            self.model.operator_id == operator_id,
            self.model.status == OperatorStatus.ASSIGNED
        ).options(
            joinedload(self.model.lodge)
        )

        return db.execute(stmt).scalar_one_or_none()


    def get_assignment_by_lodge_and_operator(self, db: Session, lodge_id: int, operator_id: int) -> Optional[LodgeOperator]:
        """
        Get any assignment record between a lodge and operator regardless of status.
        """
        stmt = select(self.model).where(
            self.model.lodge_id == lodge_id,
            self.model.operator_id == operator_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def assign_operator(self, db: Session, lodge_id: int, operator_id: int) -> LodgeOperator:
        """
        Assign an operator to a lodge. If an assignment previously existed (e.g. was REVOKED),
        reactivate it. Otherwise, create a new record.
        """
        existing = self.get_assignment_by_lodge_and_operator(db, lodge_id=lodge_id, operator_id=operator_id)
        if existing:
            existing.status = OperatorStatus.ASSIGNED
            existing.revoked_at = None
            db.commit()
            db.refresh(existing)
            return existing

        new_assignment = self.model(
            lodge_id=lodge_id,
            operator_id=operator_id,
            status=OperatorStatus.ASSIGNED
        )
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        return new_assignment

    def mark_as_revoked(self, db: Session, assignment: LodgeOperator) -> LodgeOperator:
        """
        Pure DB update to mark an active operator assignment as REVOKED.
        """
        assignment.status = OperatorStatus.REVOKED
        assignment.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(assignment)
        return assignment

    def get_operators_for_lodge(self, db: Session, lodge_id: int) -> List[LodgeOperator]:
        """
        List all active operator assignments for a given lodge.
        """
        stmt = select(self.model).options(
            joinedload(self.model.operator)
        ).where(
            self.model.lodge_id == lodge_id,
            self.model.status == OperatorStatus.ASSIGNED
        )
        return list(db.execute(stmt).scalars().all())

    def get_active_lodges_for_operator(self, db: Session, operator_id: int, skip: int = 0, limit: int = 20
                                       ) -> List[Lodge]:
        """
        Get all lodges that an operator is actively assigned to.
        """
        stmt = select(Lodge).join(
            self.model, and_(
                self.model.lodge_id == Lodge.id,
                self.model.operator_id == operator_id,
                self.model.status == OperatorStatus.ASSIGNED
            )
        ).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())


crud_lodge_operator = CRUDLodgeOperator()
