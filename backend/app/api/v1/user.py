"""
API routes for user management.

Provides endpoints for user registration (landlords and tenants) and authentication (login).
"""

from fastapi import APIRouter, Depends
from fastapi import Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas import user as schema_user
from app.schemas import tenantprofile as schema_tenant
from app.schemas.error import ErrorResponseSchema
from app.services import user_service, tenant_services

router = APIRouter()


@router.post(
    '/register/landlord',
    response_model=schema_user.UserResponse,
    status_code=201,
    summary="Register a new landlord",
    description="Creates a new landlord account. The email must be unique across the system.",
    response_description="The newly created landlord user",
    responses={
        400: {
            "model": ErrorResponseSchema,
            "description": "A user with this email already exists in the system",
        },
    },
)
def register_landlord(
        landlord_in: schema_user.UserCreate,
        db: Session = Depends(get_db)
):
    """
    Register a new landlord user.

    Args:
        landlord_in (schema_user.UserCreate): The registration data for the landlord.
        db (Session): The database session.

    Returns:
        schema_user.UserResponse: The newly created landlord user.
    """

    return user_service.sign_up_landlord(db=db, landlord_data=landlord_in)


@router.post(
    '/register/operator',
    response_model=schema_user.UserResponse,
    status_code=201,
    summary="Register a new operator",
    description="Creates a new operator account for pilot testing. The email must be unique across the system.",
    response_description="The newly created operator user",
    responses={
        400: {
            "model": ErrorResponseSchema,
            "description": "A user with this email already exists in the system",
        },
    },
)
def register_operator(
        operator_in: schema_user.UserCreate,
        db: Session = Depends(get_db)
):
    """
    Register a new operator user.

    Args:
        operator_in (schema_user.UserCreate): The registration data for the operator.
        db (Session): The database session.

    Returns:
        schema_user.UserResponse: The newly created operator user.
    """
    return user_service.sign_up_operator(db=db, operator_data=operator_in)



@router.post(
    '/register/tenant',
    response_model=schema_tenant.TenantProfileResponse,
    status_code=201,
    summary="Register a new tenant via invite",
    description="Creates a new tenant profile using a valid invitation link. The invite must not be expired or already accepted.",
    response_description="The newly created tenant profile",
    responses={
        400: {
            "model": ErrorResponseSchema,
            "description": "A user with this email already exists in the system, or the invitation has already been accepted or has expired",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "The invitation ID does not exist",
        },
    },
)
def register_tenant(
        tenant_in: schema_tenant.TenantProfileCreate,
        db: Session = Depends(get_db)
):
    """
    Register a new tenant user profile.

    Args:
        tenant_in (schema_tenant.TenantProfileCreate): The registration data for the tenant.
        db (Session): The database session.

    Returns:
        schema_tenant.TenantProfileResponse: The newly created tenant profile.
    """

    return tenant_services.sign_up_tenant(db=db, tenant_in=tenant_in)




@router.post(
    '/login',
    response_model=schema_user.UserResponse,
    summary="Authenticate user",
    description="Authenticates a user with email and password. Returns access and refresh tokens set as HTTP-only cookies.",
    response_description="Authenticated user details with tokens",
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Invalid email or password",
        },
    },
)
def login_user(
        response: Response,
        db: Session = Depends(get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate a user and return an access token.

    Args:
        response:
        db (Session): The database session.
        form_data (OAuth2PasswordRequestForm): The login credentials (username/email and password).

    Returns:
        schema_user.Token: The authentication token.
    """

    return user_service.login_authenticated_user(db, email=form_data.username.lower(),
                                                 response=response, password=form_data.password)


@router.post(
    '/refresh',
    response_model=schema_user.UserResponse,
    summary="Refresh access token",
    description="Uses the refresh token from the HTTP-only cookie to generate a new access token.",
    response_description="User details with new tokens",
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Refresh token is invalid, expired, or does not match any active session",
        },
        404: {
            "model": ErrorResponseSchema,
            "description": "The user associated with the token no longer exists or is deactivated",
        },
    },
)
def refresh_token(response: Response, refresh_token: str = Cookie(None), db: Session = Depends(get_db)):
    return user_service.refresh_access_token(db, response=response, refresh_token=refresh_token)


@router.get(
    '/me',
    response_model=schema_user.UserResponse,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
    response_description="Current user profile",
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Missing, invalid, or expired access token",
        },
    },
)
def get_me(
        authenticated_user: User = Depends(get_current_user)
):
    return authenticated_user

@router.post(
    '/logout',
    summary="Logout user",
    description="Invalidates the current refresh token and clears authentication cookies.",
    response_description="Logout confirmation",
    responses={
        401: {
            "model": ErrorResponseSchema,
            "description": "Missing, invalid, or expired access token",
        },
    },
)
def logout_user(
        response: Response,
        db: Session = Depends(get_db),
        refresh_token: str = Cookie(None),
        current_user: User = Depends(get_current_user)
):
    return user_service.logout_authenticated_user(db, response=response, refresh_token=refresh_token,
                                                  user_id=current_user.id)