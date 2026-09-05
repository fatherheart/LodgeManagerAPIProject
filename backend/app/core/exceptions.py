from typing import Optional, Any
from uuid import UUID

from starlette import status

from app.core.enums import LeaseStatus, RoomStatus, InviteStatus


class BaseLodgeOpsError(Exception):
    def __init__(self, detail: str, meta: dict = None, status_code: int = 400 ):
        self.status_code = status_code
        self.detail = detail
        self.meta = meta or {}
        super().__init__(self.detail)


class BaseAlreadyExistError(BaseLodgeOpsError):
    def __init__(self, entity_name: Optional[str], exception_name: str):
        self.entity_name = entity_name
        self.exception_name = exception_name
        self.detail = f'{self.exception_name.title()}: {self.entity_name} already exists'
        super().__init__(self.detail, status_code=400)


class UserAlreadyExistError(BaseAlreadyExistError):
    def __init__(self, email: str):
        super().__init__(entity_name=email, exception_name='User')


class LodgeAlreadyExistError(BaseAlreadyExistError):
    def __init__(self, name: str):
        super().__init__(entity_name=name, exception_name='Lodge')

class RoomAlreadyExistError(BaseAlreadyExistError):
    def __init__(self, room_name: str):
        super().__init__(entity_name=room_name, exception_name='Room')


class PendingTenantNotAllowed(BaseLodgeOpsError):
    def __init__(self, tenant_id: int | None = None):
        self.detail = 'Cannot create lease for a pending applicant. Onboard them via invitation approval instead.'
        meta = {'tenant_id': tenant_id} if tenant_id else {}
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST, meta=meta)



class InvalidActionError(BaseLodgeOpsError):
    def __init__(self, error_name: str, error_value: str, error_status: int= status.HTTP_400_BAD_REQUEST):
        self.detail = f'{error_name.title()} is already {error_value.title()}'
        super().__init__(detail=self.detail, status_code=error_status)


class InvalidLeaseActionError(InvalidActionError):
    def __init__(self, lease_status: LeaseStatus ):
        super().__init__(error_name='Lease', error_value=lease_status.value)

class InvalidInvitation(InvalidActionError):
    def __init__(self, invite_status: InviteStatus):
        super().__init__(error_name='Invite', error_value=invite_status.value)





class BaseMaxLimitReachedError(BaseLodgeOpsError):
    def __init__(self, detail: str, meta: dict = None):
        super().__init__(detail=detail, status_code=400, meta=meta)

class RentAmtExceededError(BaseMaxLimitReachedError):
    def __init__(self, agreed, current_total, attempted):
        self.remaining = agreed - current_total
        self.detail = f"Remaining balance is ₦{self.remaining:,}. You attempted to pay ₦{attempted:,}."
        self.meta  = {
            'remaining': self.remaining,
            'current_total': current_total,
            'agreed_rent': agreed
        }
        super().__init__(detail=self.detail, meta=self.meta)


class BaseNotFoundError(BaseLodgeOpsError):
    def __init__(self, name:str):
        self.detail = f'{name.title()} could not be found'
        super().__init__(detail=self.detail, status_code=404, )
        
        
class UserNotFoundError(BaseNotFoundError):
    def __init__(self):
        super().__init__(name="User")

class LodgeNotFoundError(BaseNotFoundError):
    def __init__(self):
        super().__init__(name='Lodge')


class RoomNotFoundError(BaseNotFoundError):
    def __init__(self, room_no: str = None, detail: str = ''):
        self.meta = ({
            'room_no': room_no
        })
        self.detail = detail
        super().__init__(name='Room' if not detail else detail)

class LeaseNotFoundError(BaseNotFoundError):
    def __init__(self):
        super().__init__(name='Lease')

class TenantProfileNotFoundError(BaseNotFoundError):
    def __init__(self):
        super().__init__(name='TenantProfile')


class UnauthorizedAccessError(BaseLodgeOpsError):
    def __init__(self):
        self.detail = f'Invalid email or password.'
        super().__init__(detail=self.detail, status_code=401)
        

class BaseNotAllowedError(BaseLodgeOpsError):
    def __init__(self, entity_name):
        self.detail = f'Only {entity_name} are allowed.'
        super().__init__(detail=self.detail, status_code=403)


class NotLandlordError(BaseNotAllowedError):
    def __init__(self):
        super().__init__(entity_name='landlords')


class NotTenantError(BaseNotAllowedError):
    def __init__(self):
        super().__init__(entity_name='tenants')


class NotLodgeOperatorError(BaseNotAllowedError):
    def __init__(self):
        super().__init__(entity_name='assigned operators')


class NotOperatorOrLandlordError(BaseNotAllowedError):
    def __init__(self):
        super().__init__(entity_name='operators or landlords')



class InvalidCredentialsError(BaseLodgeOpsError):

    def __init__(self):
        self.detail = 'could not validate credentials'
        super().__init__(detail=self.detail, status_code=status.HTTP_401_UNAUTHORIZED)

class RoomIsOccupiedError(BaseLodgeOpsError):
    def __init__(self, occupied_room_no: str):
        self.detail = "Cannot update an occupied room. Terminate the lease first."
        self.meta = {
            'occupied_room_no ': occupied_room_no
        }

        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST, meta=self.meta)

class NotUpdatableOptionError(BaseLodgeOpsError):
    def __init__(self, update_status: RoomStatus, allowed_options: list[RoomStatus]):
        self.message = f'{update_status.value} is not an updatable option'

        self.meta = {
            'provided': f'{update_status.value}' ,
            'allowed_options': ', '.join([opt.value for opt in allowed_options])
        }
        super().__init__(detail=self.message, status_code=status.HTTP_400_BAD_REQUEST)


class InviteNotFoundError(BaseNotFoundError):
    def __init__(self, invite_id: UUID | None = None, name: str = 'Invite'):
        self.meta = {
            'invite_id': invite_id
        } if invite_id else {}

        super().__init__(name=name)


class UnapprovedTenantError(BaseLodgeOpsError):
    def __init__(self, tenant_id: int):
        self.msg = f'Tenant is not approved by operator.'
        self.meta = {
            'tenant_id': tenant_id
        }

        super().__init__(detail=self.msg, status_code=status.HTTP_400_BAD_REQUEST)




class RoomNotAvailableError(BaseLodgeOpsError):
    def __init__(self, room_no: str, room_status: str):
        self.detail = f"Room {room_no} is currently {room_status} and cannot receive new invitations."
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST)


class TenantHasActiveLeaseError(BaseLodgeOpsError):
    def __init__(self):
        super().__init__(
            detail="Cannot reject a tenant with active leases. Terminate all leases first.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class NotLodgeOwnerError(BaseNotAllowedError):
    def __init__(self):
        super().__init__(entity_name='the lodge owner')


# Reusable subclasses for backwards compatibility and exact error metadata
class OwnershipInviteNotFoundError(InviteNotFoundError):
    def __init__(self, invite_id: UUID | None = None):
        super().__init__(invite_id=invite_id, name='Ownership Invitation')


class OperatorInviteNotFoundError(InviteNotFoundError):
    def __init__(self, invite_id: UUID | None = None):
        super().__init__(invite_id=invite_id, name='Operator Invitation')



class PhoneMismatchError(BaseLodgeOpsError):
    def __init__(self, target_phone: str, user_phone: str):
        self.detail = "This invitation is tied to a different phone number."
        self.meta = {'expected': target_phone, 'provided': user_phone}
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST, meta=self.meta)


class InviteExpiredError(BaseLodgeOpsError):
    def __init__(self):
        self.detail = "This invitation has expired."
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST)


class InviteAlreadyConsumedError(BaseLodgeOpsError):
    def __init__(self):
        self.detail = "This invitation has already been claimed or accepted."
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST)


class LodgeAlreadyClaimedError(BaseLodgeOpsError):
    def __init__(self):
        self.detail = "This lodge has already been claimed by an owner."
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST)


class OperatorAlreadyAssignedError(BaseLodgeOpsError):
    def __init__(self, operator_id: int):
        self.detail = f"Operator {operator_id} is already actively assigned to this lodge."
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST)


class OperatorNotAssignedError(BaseLodgeOpsError):
    def __init__(self, operator_id: Optional[int] = None):
        if operator_id:
            self.detail = f"Operator {operator_id} is not actively assigned to this lodge."
        else:
            self.detail = "Operator is not actively assigned to this lodge."
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST)


class InviteAlreadyCancelledError(BaseLodgeOpsError):
    def __init__(self):
        self.detail = "This invitation has already been cancelled."
        super().__init__(detail=self.detail, status_code=status.HTTP_400_BAD_REQUEST)


class NotInviteCreatorError(BaseLodgeOpsError):
    def __init__(self):
        self.detail = "Only the operator who created this invitation can cancel it."
        super().__init__(detail=self.detail, status_code=status.HTTP_403_FORBIDDEN)


