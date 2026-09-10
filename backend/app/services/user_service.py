"""
Module providing user-related business logic.

This module contains services for managing users, including authentication.
"""
import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from fastapi import Response, Cookie
from app.core.config import settings
from app.crud.user import crud_user
from app.core.enums import UserRole
from app.core.exceptions import UserAlreadyExistError, UnauthorizedAccessError, UserNotFoundError, \
    InvalidCredentialsError, BaseNotFoundError
from app.core.security import verify_password_hash, get_password_hash, create_access_token, create_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.refresh_token import RefreshTokenInternal
from app.schemas.user import UserCreate, UserInternal


def setup_signup_data_internal(db: Session, signup_data: UserCreate, role: UserRole):
    user = crud_user.get_user_by_email(db, email=signup_data.email)

    if user:
        raise UserAlreadyExistError(email=signup_data.email)

    hashed = get_password_hash(signup_data.password)

    base_user_data = UserInternal(
        **signup_data.model_dump(exclude={'password'}),
        hashed_password=hashed,
        role=role
    )

    return base_user_data

def sign_up_landlord(
        db: Session,
        landlord_data: UserCreate,
) -> User:
    """
    Sign up a new landlord.

    Args:
        db (Session): The database session.
        landlord_data (UserCreate): The data for the new landlord.

    Returns:
        User: The newly created user.
    """
    landlord_internal_data = setup_signup_data_internal(db, signup_data=landlord_data, role=UserRole.LANDLORD)
    return crud_user.create(db, obj_in=landlord_internal_data)

def sign_up_operator(
        db: Session,
        operator_data: UserCreate,
) -> User:
    """
    Sign up a new pilot operator.

    Args:
        db (Session): The database session.
        operator_data (UserCreate): The data for the new operator.

    Returns:
        User: The newly created operator user.
    """
    operator_internal_signup_data =  setup_signup_data_internal(db, signup_data=operator_data, role=UserRole.OPERATOR)
    return crud_user.create(db, obj_in=operator_internal_signup_data)

def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticates a user by checking their email and password.

    Args:
        db (Session): The database session.
        email (str): The email address of the user.
        password (str): The plain text password.

    Returns:
        User: The authenticated user object.
    """
    user = crud_user.get_user_by_email(db, email=email)
    if not user:
        raise UnauthorizedAccessError()

    if not verify_password_hash(password, user.hashed_password):
        raise UnauthorizedAccessError()

    return user


def login_authenticated_user(
        db: Session,
        response: Response,
        email: str,
        password: str
):
    """
    Log in an authenticated user and generate an access token.

    Args:
        response: for attaching cookies
        db (Session): The database session.
        email (str): The email address of the user.
        password (str): The plain text password.

    Returns:
        dict: A dictionary containing the access token and token type.
    """
    authenticated_user = authenticate_user(db, email=email, password=password)

    if not authenticated_user:
        raise UnauthorizedAccessError()

    access_token = create_access_token(
        subject=str(authenticated_user.id)
    )

    new_refresh_token = _refresh_record_sequence(db, user_id=authenticated_user.id)

    response.set_cookie(
        key='access_token',
        value=access_token,
        secure=False,
        httponly=True,
        samesite='lax',
        path='/'
    )
    response.set_cookie(
        key='refresh_token',
        value=new_refresh_token,
        secure=False,
        httponly=True,
        path="/api/v1/auth",
        samesite='lax'
    )
    return authenticated_user


def _refresh_record_sequence(db: Session, user_id: int, db_refresh_token: RefreshToken = None) -> str:
    if db_refresh_token:
        crud_user.delete_refresh_token(db, db_refresh_token=db_refresh_token, user_id=user_id)

    new_refresh_token_str = create_refresh_token(subject=str(user_id))

    refresh_token_schema = RefreshTokenInternal(user_id=user_id, token=new_refresh_token_str)
    new_refresh_record = crud_user.create_new_refresh_token_record(db, refresh_in=refresh_token_schema)

    return new_refresh_record.token


def refresh_access_token(db: Session, response: Response, refresh_token: str| None):
    current_refresh_token = refresh_token
    try:
        payload = jwt.decode(
            current_refresh_token,
            key=settings.REFRESH_SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except (jwt.PyJWTError, ValueError, ValidationError):
        raise InvalidCredentialsError()

    if payload.get('type') != 'refresh':
        raise InvalidCredentialsError()

    user_id = payload.get('sub')

    current_user: User = crud_user.get(db=db, item_id=user_id)

    if not current_user or not current_user.is_active:
        raise UserNotFoundError()

    db_refresh_token = crud_user.get_refresh_token(db, refresh_token=current_refresh_token, user_id=current_user.id)

    if not db_refresh_token:
        raise InvalidCredentialsError()

    access_token = create_access_token(str(current_user.id))
    new_refresh_token = _refresh_record_sequence(db, user_id=user_id, db_refresh_token=db_refresh_token)

    response.set_cookie(
        key='access_token',
        value=access_token,
        secure=True,
        httponly=True,
        samesite='lax',
        path='/'
    )
    response.set_cookie(
        key='refresh_token',
        value=new_refresh_token,
        secure=True,
        httponly=True,
        path="/api/v1/auth",
        samesite='lax'
    )
    return current_user


def logout_authenticated_user(db: Session, response: Response, refresh_token: str | None, user_id: int):
    db_refresh_token = crud_user.get_refresh_token(db, refresh_token=refresh_token, user_id=user_id)
    if not db_refresh_token:
        raise  BaseNotFoundError('RefreshToken')

    crud_user.delete_refresh_token(db, db_refresh_token=db_refresh_token, user_id=user_id)

    response.delete_cookie("access_token", httponly=True, secure=True, samesite="lax", path='/')
    response.delete_cookie("refresh_token", httponly=True, secure=True, samesite="lax", path="/api/v1/auth")
    return {"detail": "Successfully logged out"}
