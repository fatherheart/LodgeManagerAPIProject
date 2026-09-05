"""
Dependency injection module for the FastAPI application.

Provides dependencies for database session management and user authentication.
"""
import jwt
from fastapi import Cookie
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (NotLandlordError, NotTenantError, UserNotFoundError,
                                 InvalidCredentialsError)
from app.db.session import SessionLocal
from typing import Generator
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from app.crud.user import crud_user
from app.models.user import User
from app.services.lodge_service import is_landlord, is_tenant

#helps to extract token from http request
oauth_2 = OAuth2PasswordBearer(
    tokenUrl='/api/v1/auth/login',
    auto_error=False
)


def get_db() -> Generator:
    """
    Get a database session generator.

    Yields:
        Session: The database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
        db: Session = Depends(get_db),
        access_token: str = Cookie(None),
        bearer_token: str = Depends(oauth_2)
):
    """
    Get the currently authenticated user from cookie or Authorization header.
    """
    token = access_token or bearer_token

    if not token:
        raise InvalidCredentialsError()
    
    try:

        payload = jwt.decode(
            token,
            key=settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        user_id = payload.get('sub')
        if not user_id:
            raise InvalidCredentialsError

        if  payload.get('type') != 'access':
            raise InvalidCredentialsError

    except (jwt.PyJWTError, ValueError, ValidationError):
        raise InvalidCredentialsError()

    current_user: User = crud_user.get(db=db, item_id=user_id)

    if not current_user or not current_user.is_active:
        raise UserNotFoundError()

    return current_user


#dependency for ensuring the user is a landlord
#get the current logged in user(validated and authenticated)
#check if the user object is of the role of landlord -> allow the user to the route that needs the dependency

def get_landlord_user(
        current_user: User = Depends(get_current_user)
):
    """
    Get the current authenticated user and ensure they have a landlord role.

    Args:
        current_user (User): The current authenticated user.

    Returns:
        User: The authenticated landlord user.

    Raises:
        NotLandlordError: If the user does not have a landlord role.
    """
    if not is_landlord(current_user.role):
       raise NotLandlordError()
    return current_user


def get_tenant_user(
        current_user: User = Depends(get_current_user)
):
    """
    Get the current authenticated user and ensure they have a tenant role.

    Args:
        current_user (User): The current authenticated user.

    Returns:
        User: The authenticated tenant user.

    Raises:
        NotTenantError: If the user does not have a tenant role.
    """
    if not is_tenant(current_user.role):
        raise NotTenantError()
    return current_user




def get_operator_or_landlord_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Route Gate: Ensure the user has either an OPERATOR or LANDLORD role.
    Stops tenants and invalid roles at the HTTP boundary.
    """
    from app.services.lodge_service import is_operator_or_landlord
    from app.core.exceptions import NotOperatorOrLandlordError

    if not is_operator_or_landlord(current_user.role):
        raise NotOperatorOrLandlordError()
    return current_user




