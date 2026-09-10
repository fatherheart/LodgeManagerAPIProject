from datetime import datetime, timedelta, date
from uuid import uuid7
import random
import pytest

from app.core.enums import StudentLevel, TenantType
from app.models.tenantprofile import TenantProfile
from app.schemas import invitation as schema_invite
from app.schemas import tenantprofile as schema_tenant
from app.services import room_service, invite_service, tenant_services


@pytest.fixture
def invite_schema_factory():
    def _create(
        room_id: int = 1,
        expires_at: datetime = None,
        lodge_id: int = 1
    ):
        if expires_at is None:
            expires_at = datetime.now() + timedelta(days=7)
        return schema_invite.InviteCreate(
            room_id=room_id,
            expires_at=expires_at,
            lodge_id=lodge_id
        )
    return _create


@pytest.fixture
def pilot_tenant_invite(test_db, invite_schema_factory, operator_pilot_lodge, operator_user, room_schema_factory):
    """
    Active tenant invite issued by operator Musa for a room in his pilot lodge.
    """
    rm_schema = room_schema_factory(lodge_id=operator_pilot_lodge.id, room_no="Invited Room 101")
    room = room_service.create_room_for_lodge(test_db, room_in=rm_schema, current_user=operator_user)
    inv_schema = invite_schema_factory(
        room_id=room.id,
        lodge_id=operator_pilot_lodge.id,
    )
    return invite_service.invite_tenant(
        test_db, invite_in=inv_schema, current_user=operator_user
    )


@pytest.fixture
def tenant_schema_factory(user_schema_factory):
    """
    A pytest fixture that provides a factory for creating tenant schemas.
    """
    def _create(**kwargs):
        defaults = {
            "first_name": "Tenant",
            "last_name": "Resident",
            "email": "tenant@test.com",
            "password": "Tenant12345",
            "phone_no": "08108417160",
            "level": StudentLevel.LEVEL_200,
            "tenant_type": TenantType.STUDENT,
            "emergency_contact_name": "Mrs. Bond",
            "emergency_contact_phone_no": "0834124859",
            "reg_no": random.randint(1000000, 9999999),
            "invite_id": uuid7()
        }
        defaults.update(kwargs)

        user_field_keys = user_schema_factory().model_fields.keys()
        tenant_field_keys = schema_tenant.TenantBase.model_fields.keys()

        user_data = {k: v for k, v in defaults.items() if k in user_field_keys}
        tenant_data = {k: v for k, v in defaults.items() if k in tenant_field_keys}

        return schema_tenant.TenantProfileCreate(
            user_info=user_schema_factory(**user_data),
            tenant_info=schema_tenant.TenantBase(**tenant_data),
            invite_id=defaults["invite_id"]
        )
    return _create


@pytest.fixture
def mock_tenant_schema(tenant_schema_factory, pilot_tenant_invite):
    """
    A pytest fixture that provides a mock tenant schema.
    """
    return tenant_schema_factory(invite_id=pilot_tenant_invite.id)


@pytest.fixture
def pilot_pending_tenant(test_db, mock_tenant_schema):
    """
    A pytest fixture that adds a registered/pending tenant to the database.
    """
    return tenant_services.sign_up_tenant(test_db, tenant_in=mock_tenant_schema)


@pytest.fixture
def pilot_pending_tenants_batch(
    test_db,
    tenant_schema_factory,
    operator_pilot_lodge,
    invite_schema_factory,
    operator_user,
    room_schema_factory
):
    """
    A pytest fixture that seeds 5 pending tenants in the operator's pilot lodge for listing & pagination tests.
    """
    db_tenants: list[TenantProfile] = []
    for i in range(5):
        rm_schema = room_schema_factory(
            room_no=f'Pilot-Tenant-Rm-{i + 1}',
            lodge_id=operator_pilot_lodge.id
        )
        room = room_service.create_room_for_lodge(test_db, room_in=rm_schema, current_user=operator_user)
        inv_schema = invite_schema_factory(lodge_id=operator_pilot_lodge.id, room_id=room.id)
        db_invite = invite_service.invite_tenant(test_db, invite_in=inv_schema, current_user=operator_user)
        t_schema = tenant_schema_factory(
            first_name=f'OperatorTenant{i + 1}',
            last_name=f'Test{i + 1}',
            email=f'pilot_tenant_{i + 1}@test.com',
            invite_id=db_invite.id
        )
        new_tenant = tenant_services.sign_up_tenant(test_db, tenant_in=t_schema)
        db_tenants.append(new_tenant)
    return db_tenants


@pytest.fixture
def pilot_pending_tenants_pool(
    test_db,
    tenant_schema_factory,
    operator_pilot_lodge,
    invite_schema_factory,
    operator_user,
    room_schema_factory
):
    """
    A pytest fixture that seeds 10 pending tenants in the operator's pilot lodge.
    """
    max_tenants = 10
    db_tenants: list[TenantProfile] = []
    for i in range(max_tenants):
        rm_schema = room_schema_factory(
            room_no=f'Tenant-Rm-{i + 1}',
            lodge_id=operator_pilot_lodge.id
        )
        room = room_service.create_room_for_lodge(test_db, room_in=rm_schema, current_user=operator_user)
        inv_schema = invite_schema_factory(lodge_id=operator_pilot_lodge.id, room_id=room.id)
        db_invite = invite_service.invite_tenant(test_db, invite_in=inv_schema, current_user=operator_user)
        t_schema = tenant_schema_factory(
            first_name=f'TenantFirst{i + 1}',
            last_name=f'TenantLast{i + 1}',
            email=f'tenant{i + 1}@test.com',
            invite_id=db_invite.id
        )
        new_tenant = tenant_services.sign_up_tenant(test_db, tenant_in=t_schema)
        db_tenants.append(new_tenant)
    return db_tenants


@pytest.fixture
def authenticated_tenant_client(auth_client_factory, pilot_pending_tenant):
    """
    A pytest fixture that provides an authenticated client for a tenant.
    """
    tenant = pilot_pending_tenant
    client = auth_client_factory(user_id=tenant.user_id)
    client.tenant = tenant
    return client


@pytest.fixture
def second_tenant_in_landlord_lodge(test_db, tenant_schema_factory, landlord_claimed_lodge, invite_schema_factory, landlord_user, room_schema_factory):
    """
    A pytest fixture that adds a second tenant to the landlord's claimed lodge.
    """
    from app.crud.crud_lodge_operator import crud_lodge_operator
    crud_lodge_operator.assign_operator(test_db, lodge_id=landlord_claimed_lodge.id, operator_id=landlord_user.id)

    rm_schema = room_schema_factory(lodge_id=landlord_claimed_lodge.id, room_no="Second Tenant Rm")
    room = room_service.create_room_for_lodge(test_db, room_in=rm_schema, current_user=landlord_user)
    inv_schema = invite_schema_factory(lodge_id=landlord_claimed_lodge.id, room_id=room.id)
    db_invite = invite_service.invite_tenant(test_db, invite_in=inv_schema, current_user=landlord_user)

    t_schema = tenant_schema_factory(email="tenant2@test.com", first_name="TenantB", invite_id=db_invite.id)
    return tenant_services.sign_up_tenant(test_db, tenant_in=t_schema)


@pytest.fixture
def other_landlord_tenant(test_db, tenant_schema_factory, other_landlord_lodge, other_landlord_user, invite_schema_factory, room_schema_factory):
    """
    A pytest fixture that adds a tenant to a different landlord's lodge.
    """
    from app.crud.crud_lodge_operator import crud_lodge_operator
    crud_lodge_operator.assign_operator(test_db, lodge_id=other_landlord_lodge.id, operator_id=other_landlord_user.id)

    rm_schema = room_schema_factory(lodge_id=other_landlord_lodge.id, room_no="Diff Landlord Rm")
    room = room_service.create_room_for_lodge(test_db, room_in=rm_schema, current_user=other_landlord_user)
    inv_schema = invite_schema_factory(lodge_id=other_landlord_lodge.id, room_id=room.id)
    db_invite = invite_service.invite_tenant(test_db, invite_in=inv_schema, current_user=other_landlord_user)
    t_schema = tenant_schema_factory(email="tenant3@test.com", invite_id=db_invite.id)
    return tenant_services.sign_up_tenant(test_db, tenant_in=t_schema)


@pytest.fixture
def tenant_approval_schema_factory():
    def _create(
        start_date: date = date.today(),
        end_date: date = date.today() + timedelta(days=365),
        agreed_rent_amt: int = 250000,
        total_amt_paid: int = 250000
    ):
        return schema_tenant.TenantApprovalCreate(
            start_date=start_date,
            end_date=end_date,
            agreed_rent_amt=agreed_rent_amt,
            total_amt_paid=total_amt_paid
        )
    return _create


@pytest.fixture
def mock_tenant_approval_schema(tenant_approval_schema_factory):
    return tenant_approval_schema_factory()
