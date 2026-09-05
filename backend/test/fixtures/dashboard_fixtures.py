from datetime import date, timedelta
import pytest

from app.core.enums import RoomStatus, LeaseStatus, TenantStatus
from app.schemas.dashboard import DashboardFilters
from app.services import room_service, invite_service, tenant_services, lease_services, dashboard_service


@pytest.fixture
def pilot_dashboard_metrics_data(
    test_db,
    operator_pilot_lodge,
    operator_user,
    room_schema_factory,
    tenant_schema_factory,
    lease_schema_factory,
    payment_schema_factory,
    invite_schema_factory
):
    lodge_id = operator_pilot_lodge.id
    operator = operator_user

    room_counter = 1

    def _create_room_with_scenario(scenario: str):
        nonlocal room_counter

        room_no = f'test rm {room_counter}'

        room_data = room_schema_factory(room_no=room_no, base_rent_price=5000, lodge_id=lodge_id)
        room = room_service.create_room_for_lodge(test_db, room_in=room_data, current_user=operator)

        if scenario == "MAINTENANCE":
            room.status = RoomStatus.MAINTENANCE
            test_db.commit()
            room_counter += 1
            return
        elif scenario == "VACANT":
            room_counter += 1
            return

        inv_schema = invite_schema_factory(lodge_id=lodge_id, room_id=room.id)
        db_invite = invite_service.invite_tenant(test_db, invite_in=inv_schema, current_user=operator)

        t_schema = tenant_schema_factory(
            first_name=f"{scenario}{room_counter}",
            email=f"t{room_counter}@test.com",
            invite_id=db_invite.id
        )
        tenant = tenant_services.sign_up_tenant(test_db, tenant_in=t_schema)

        start_date = date.today() - timedelta(days=100)
        end_date = date.today() + timedelta(days=100)
        status = LeaseStatus.ACTIVE
        total_paid = 5000

        if scenario == "SAFE":
            end_date = date.today() + timedelta(days=100)
        elif scenario == "EXPIRING":
            end_date = date.today() + timedelta(days=45)
        elif scenario == "OVERDUE":
            end_date = date.today() - timedelta(days=10)
        elif scenario == "PENDING_MOVEOUT":
            status = LeaseStatus.PENDING_TERMINATION
        elif scenario == "OWING":
            total_paid = 2000
        elif scenario == "PENDING_OWING":
            status = LeaseStatus.PENDING_TERMINATION
            total_paid = 2000

        tenant.status = TenantStatus.APPROVED
        test_db.commit()
        lease_data = lease_schema_factory(
            tenant_id=tenant.id,
            room_id=room.id,
            agreed_rent_amt=5000,
            total_amt_paid=total_paid,
            start_date=start_date,
            end_date=end_date
        )

        db_lease = lease_services.create_new_lease_for_existing_tenant(
            test_db,
            lease_data=lease_data,
            current_user=operator
        )

        if scenario in ['PENDING_MOVEOUT', 'PENDING_OWING']:
            db_lease.status = status
            test_db.commit()

        room_counter += 1

    scenarios = ["VACANT", "MAINTENANCE", "SAFE", "EXPIRING", "OVERDUE", "OWING"]
    for sc in scenarios:
        for _ in range(3):
            _create_room_with_scenario(sc)

    for _ in range(2):
        _create_room_with_scenario("PENDING_MOVEOUT")

    for _ in range(1):
        _create_room_with_scenario("PENDING_OWING")

    all_filters = DashboardFilters(
        room_status_filters=[],
        financial_filters=[]
    )
    db_landlord_dashboard_stats = dashboard_service.get_landlord_dashboard(
        test_db,
        lodge_id=lodge_id,
        current_user=operator,
        filter_by=all_filters
    )
    return lodge_id, db_landlord_dashboard_stats
