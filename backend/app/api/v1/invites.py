from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status

from app.api.deps import get_db, get_operator_or_landlord_user, get_landlord_user
from app.models.user import User
from app.schemas import invitation as schema_invite
from app.schemas.ownership_invite import (
    OwnershipInviteCreate,
    OwnershipInviteResponse,
    OwnershipInviteDetail
)
from app.schemas.lodge import LodgeResponse
from app.schemas.error import ErrorResponseSchema
from app.services import invite_service, ownership_invite_service

router = APIRouter()


# =========================================================================
# 1. TENANT ROOM INVITATIONS
# =========================================================================

@router.post(
    '/',
    response_model=schema_invite.InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant invitation",
    description="Generates or returns an active invitation link for a vacant room.",
    response_description="The created or active invitation with its UUID link",
    responses={
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized managers can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Room does not exist or user does not have access"},
    },
)
def invite_tenant(
    invite_in: schema_invite.InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):

    return invite_service.invite_tenant(
        db=db,
        invite_in=invite_in,
        current_user=current_user
    )


@router.get(
    '/{invite_id}',
    response_model=schema_invite.InviteDetail,
    summary="Get invitation details",
    description="Retrieves the details of a specific invitation. Public endpoint used by prospective tenants.",
    response_description="Invitation details including lodge name and expiry status",
    responses={
        404: {"model": ErrorResponseSchema, "description": "The invitation ID does not exist"},
    },
)
def get_invite_by_id(
    invite_id: UUID,
    db: Session = Depends(get_db),
):
    return invite_service.fetch_invite_record(db=db, invite_id=invite_id)


# =========================================================================
# 2. LODGE OWNERSHIP INVITATIONS
# =========================================================================

@router.post(
    '/ownership',
    response_model=OwnershipInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a lodge ownership invite",
    description="Creates a phone-locked ownership invitation for a landlord to claim an unclaimed lodge. Idempotent.",
    response_description="The generated or existing active ownership invitation",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Lodge has already been claimed"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only authorized operators can perform this action"},
        404: {"model": ErrorResponseSchema, "description": "Lodge does not exist or user is not assigned"},
    },
)
def create_ownership_invite(
    invite_in: OwnershipInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    return ownership_invite_service.create_ownership_invite(
        db=db,
        invite_in=invite_in,
        current_user=current_user
    )


@router.get(
    '/ownership/{invite_id}',
    response_model=OwnershipInviteDetail,
    summary="Preview an ownership invite",
    description="Public endpoint to inspect an ownership invite by UUID token and verify its validity.",
    response_description="Ownership invite preview details",
    responses={
        404: {"model": ErrorResponseSchema, "description": "The ownership invitation ID does not exist"},
    },
)
def get_ownership_invite(
    invite_id: UUID,
    db: Session = Depends(get_db),
):
    return ownership_invite_service.fetch_ownership_invite(
        db=db,
        invite_id=invite_id
    )


@router.delete(
    '/ownership/{invite_id}',
    response_model=OwnershipInviteResponse,
    summary="Cancel an ownership invite",
    description="Cancels an active ownership invite before it expires. Only the creator operator can cancel.",
    response_description="The cancelled ownership invitation",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Invite is already consumed, expired, or cancelled"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only the creator operator can cancel this invite"},
        404: {"model": ErrorResponseSchema, "description": "The ownership invitation ID does not exist"},
    },
)
def cancel_ownership_invite(
    invite_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_operator_or_landlord_user)
):
    return ownership_invite_service.cancel_ownership_invite(
        db=db,
        invite_id=invite_id,
        current_user=current_user
    )


@router.post(
    '/ownership/{invite_id}/claim',
    response_model=LodgeResponse,
    summary="Claim legal ownership of a lodge",
    description="Allows an authenticated landlord with matching phone number to atomically claim ownership of an unclaimed lodge.",
    response_description="The updated lodge with landlord_id assigned",
    responses={
        400: {"model": ErrorResponseSchema, "description": "Phone mismatch, invite expired, cancelled, or already consumed"},
        401: {"model": ErrorResponseSchema, "description": "Missing, invalid, or expired access token"},
        403: {"model": ErrorResponseSchema, "description": "Only landlord accounts can claim ownership"},
        404: {"model": ErrorResponseSchema, "description": "The ownership invitation ID does not exist"},
    },
)
def claim_ownership_invite(
    invite_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_landlord_user)
):
    return ownership_invite_service.claim_ownership_invite(
        db=db,
        invite_id=invite_id,
        current_user=current_user
    )