"""
Module providing user-related CRUD operations.

This module contains the CRUD operations for User models, inheriting from
the base CRUD functionality.
"""

from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.refresh_token import RefreshTokenInternal
from app.schemas.user import UserCreate, UserUpdate


from app.crud.base_crud import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD class for User model operations.
    """

    def get_user_by_email(self, db: Session, email: str):
        """
        Get a user by their email address.

        Args:
            db (Session): The database session.
            email (str): The email address to search for.

        Returns:
            User: The found user or None.
        """
        stmt = select(self.model).filter(self.model.email == email)
        return db.execute(stmt).scalar_one_or_none()

    def get_user_by_phone(self, db: Session, phone: str):
        """
        Get a user by their phone number.
        """
        stmt = select(self.model).filter(self.model.phone_no == phone)
        return db.execute(stmt).scalar_one_or_none()


    def create_new_refresh_token_record(self, db: Session, refresh_in:RefreshTokenInternal):
        db_refresh_token = RefreshToken(**refresh_in.model_dump())
        db.add(db_refresh_token)
        db.commit()
        db.refresh(db_refresh_token)
        return db_refresh_token

    def get_refresh_token(self, db: Session, refresh_token: str, user_id: int):
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token,
                                          RefreshToken.user_id == user_id)
        return db.execute(stmt).scalar()

    def delete_refresh_token(self, db: Session, db_refresh_token: RefreshToken, user_id: int ):
        db.delete(db_refresh_token)
        db.commit()


    def delete_all_refresh_token(self,db: Session, user_id: int):
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        db.execute(stmt)
        db.commit()



crud_user = CRUDUser(User)
