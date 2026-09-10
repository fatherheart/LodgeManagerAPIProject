from datetime import date, timedelta
import random
import pytest

from app.core.enums import LeaseStatus, TenantStatus
from app.schemas import lease as schema_lease
from app.services import tenant_services, lease_services, room_service


@pytest.fixture
def lease_statuses():
    return [status for status in LeaseStatus]


@pytest.fixture
def lease_schema_factory():
    """
    A pytest fixture that provides a factory for creating LeaseCreate schemas.
    """
    def _create(
        tenant_id: int = 1,
        room_id: int = 1,
        agreed_rent_amt: int = 210000,
        total_amt_paid: int = 105000,
        start_date: date = date.today(),
        end_date: date = date.today() + timedelta(days=365),
    ):
        return schema_lease.LeaseCreate(
            tenant_id=tenant_id,
            room_id=room_id,
            agreed_rent_amt=agreed_rent_amt,
            total_amt_paid=total_amt_paid,
            start_date=start_date,
            end_date=end_date,
        )
    return _create


@pytest.fixture
def mock_lease_schema(lease_schema_factory, pilot_lodge_room, pilot_pending_tenant):
    """
    A pytest fixture that provides a mock lease schema.
    """
    return lease_schema_factory(room_id=pilot_lodge_room.id, tenant_id=pilot_pending_tenant.id)


@pytest.fixture
def pilot_active_lease(test_db, lease_schema_factory, pilot_lodge_room, pilot_pending_tenant, operator_user):
    """
    Fixture to create and add an active lease in operator's pilot lodge.
    """
    tenant_id = pilot_pending_tenant.id
    room_id = pilot_lodge_room.id

    lease_schema = lease_schema_factory(room_id=room_id, tenant_id=tenant_id)
    tenant = tenant_services.fetch_tenant_by_landlord(test_db, tenant_id=tenant_id, current_user=operator_user)
    tenant.status = TenantStatus.APPROVED
    test_db.commit()
    return lease_services.create_new_lease_for_existing_tenant(
        db=test_db,
        lease_data=lease_schema,
        current_user=operator_user
    )


@pytest.fixture
def pilot_overdue_lease(
    test_db,
    lease_schema_factory,
    operator_user,
    operator_pilot_lodge,
    pilot_pending_tenant,
    pilot_lodge_room
):
    """
    Fixture to create and add an overdue lease in operator's pilot lodge.
    """
    tenant_id = pilot_pending_tenant.id
    room_id = pilot_lodge_room.id

    tenant = tenant_services.fetch_tenant_by_landlord(test_db, tenant_id=tenant_id, current_user=operator_user)
    tenant.status = TenantStatus.APPROVED
    test_db.commit()

    return lease_services.create_new_lease_for_existing_tenant(
        test_db,
        lease_data=lease_schema_factory(
            tenant_id=tenant_id,
            room_id=room_id,
            start_date=date.today() - timedelta(days=375),
            end_date=date.today() - timedelta(days=10)
        ),
        current_user=operator_user
    )


@pytest.fixture
def pilot_terminated_lease(test_db, pilot_active_lease, operator_user):
    """
    Fixture to create and add a terminated lease in operator's pilot lodge.
    """
    lease_id = pilot_active_lease.id
    return lease_services.terminate_lease(
        test_db,
        lease_id=lease_id,
        current_user=operator_user
    )


@pytest.fixture
def pilot_pending_termination_lease(test_db, pilot_active_lease, operator_user, pilot_pending_tenant):
    """
    Fixture to create and add a lease pending termination in operator's pilot lodge.
    """
    lease_id = pilot_active_lease.id
    tenant_id = pilot_pending_tenant.id

    return lease_services.appeal_for_lease_termination(
        test_db,
        lease_id=lease_id,
        tenant_id=tenant_id
    )


@pytest.fixture
def other_landlord_active_lease(
    test_db,
    lease_schema_factory,
    other_landlord_user,
    other_landlord_tenant,
    other_landlord_room
):
    """
    Fixture to create and add an active lease to a different landlord's lodge.
    """
    lease_data = lease_schema_factory(
        tenant_id=other_landlord_tenant.id,
        room_id=other_landlord_room.id,
    )

    tenant = tenant_services.fetch_tenant_by_landlord(
        test_db,
        tenant_id=lease_data.tenant_id,
        current_user=other_landlord_user
    )
    tenant.status = TenantStatus.APPROVED
    test_db.commit()

    return lease_services.create_new_lease_for_existing_tenant(
        db=test_db,
        lease_data=lease_data,
        current_user=other_landlord_user
    )


@pytest.fixture
def pilot_leases_pool(
    test_db,
    lease_schema_factory,
    lease_statuses,
    operator_user,
    pilot_pending_tenants_pool,
    pilot_vacant_rooms_pool
):
    """
    A pytest fixture that adds multiple leases to the database in operator's pilot lodge.
    """
    db_leases = []
    num_leases_to_create = min(len(pilot_pending_tenants_pool), len(pilot_vacant_rooms_pool), 15)

    for i in range(num_leases_to_create):
        tenant = pilot_pending_tenants_pool[i]
        room = pilot_vacant_rooms_pool[i]

        lease_data = lease_schema_factory(
            tenant_id=tenant.id,
            room_id=room.id,
            agreed_rent_amt=room.base_rent_price,
            start_date=date.today() - timedelta(days=random.randint(1, 365)),
            end_date=date.today() + timedelta(days=random.randint(1, 365)),
        )
        tenant.status = TenantStatus.APPROVED
        test_db.commit()
        new_lease = lease_services.create_new_lease_for_existing_tenant(
            db=test_db,
            lease_data=lease_data,
            current_user=operator_user
        )
        db_leases.append(new_lease)
    return db_leases


@pytest.fixture
def pilot_tenant_lease_history(
    test_db,
    lease_schema_factory,
    operator_user,
    pilot_pending_tenant,
    room_schema_factory,
    operator_pilot_lodge
):
    """
    Fixture to create a history of leases for a single tenant in operator's pilot lodge.
    """
    tenant = pilot_pending_tenant
    db_leases = []
    max_history = 5
    for i in range(max_history):
        rm_schema = room_schema_factory(
            room_no=f'History Rm-{i + 1}',
            description=f'Room for history test {i + 1}',
            base_rent_price=250000,
            lodge_id=operator_pilot_lodge.id
        )
        new_room = room_service.create_room_for_lodge(test_db, current_user=operator_user, room_in=rm_schema)

        status = LeaseStatus.OVERDUE if i < 3 else LeaseStatus.ACTIVE

        lease_data = lease_schema_factory(
            tenant_id=tenant.id,
            room_id=new_room.id,
            agreed_rent_amt=new_room.base_rent_price,
            start_date=date.today() - timedelta(days=365 * (i + 1)) if status == LeaseStatus.OVERDUE else date.today() - timedelta(days=20 * (i + 1)),
            end_date=date.today() - timedelta(days=365 * i) if status == LeaseStatus.OVERDUE else (date.today() - timedelta(days=20 * (i + 1))) + timedelta(days=365),
        )

        tenant.status = TenantStatus.APPROVED
        test_db.commit()
        new_lease = lease_services.create_new_lease_for_existing_tenant(
            db=test_db,
            lease_data=lease_data,
            current_user=operator_user
        )
        db_leases.append(new_lease)

    return tenant, db_leases
