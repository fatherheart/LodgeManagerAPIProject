from typing import TypeVar, Type
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import InviteStatus
from app.crud.base_crud import ModelType
from app.schemas import invitation as schema_invite
from app.models.invitation import Invite


class CrudInvite:
    def __init__(self, model: Type[Invite]):
        self.model = model

    def add_invite_record(self, db: Session, invite_in: schema_invite.InviteCreate) -> Invite:
        db_invite = self.model(
            room_id=invite_in.room_id,
            expires_at=invite_in.expires_at
        )
        db.add(db_invite)
        db.commit()
        db.refresh(db_invite)
        return db_invite

    def get_invite_record_by_id(self, db: Session, invite_id: UUID) -> Invite | None:
        from app.models.room import Room
        options = [joinedload(self.model.room).joinedload(Room.lodge)]
        stmt = select(self.model).where(self.model.id == invite_id).options(*options)
        return db.execute(stmt).scalar()

    def get_active_invite_for_room(self, db: Session, room_id: int) -> Invite | None:
        curr_time = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = select(self.model).where(
            self.model.room_id == room_id,
            self.model.status == InviteStatus.SENT,
            self.model.expires_at > curr_time
        )
        return db.execute(stmt).scalar_one_or_none()


crud_invite = CrudInvite(Invite)