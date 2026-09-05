import pytest
from app.crud.payment import crud_payment
from app.schemas import payment as schema_payment
from app.services import payment_service


@pytest.fixture
def payment_schema_factory():
    """
    A pytest fixture that provides a factory for creating PaymentCreate schemas.
    """
    def _create(
        amount_paid: int = 50000,
        lease_id: int = 1
    ):
        return schema_payment.PaymentCreate(
            amount_paid=amount_paid,
            lease_id=lease_id
        )
    return _create


@pytest.fixture
def mock_payment_schema(payment_schema_factory):
    """
    A pytest fixture that provides a mock payment schema using the payment_schema_factory.
    """
    return payment_schema_factory()


@pytest.fixture
def pilot_rent_payment(test_db, payment_schema_factory, pilot_active_lease, operator_user):
    """
    Fixture to create and add a single payment to the database in operator's pilot lodge.
    """
    p_schema = payment_schema_factory(
        lease_id=pilot_active_lease.id
    )
    return payment_service.add_payment_record(
        db=test_db,
        current_user=operator_user,
        payment_data=p_schema
    )


@pytest.fixture
def pilot_multiple_safe_payments(test_db, payment_schema_factory, operator_user, pilot_active_lease):
    """
    Fixture to create multiple payments for a tenant's lease that stay within the agreed rent amount.
    """
    lease = pilot_active_lease
    num_payments = 5

    already_paid = crud_payment.get_payments_aggregate_by_lease_id(test_db, lease_id=lease.id)
    remaining_balance = lease.agreed_rent_amt - already_paid
    amount_per_payment = remaining_balance // num_payments

    for _ in range(num_payments):
        payment_data = payment_schema_factory(
            amount_paid=amount_per_payment,
            lease_id=lease.id
        )
        payment_service.add_payment_record(
            db=test_db,
            current_user=operator_user,
            payment_data=payment_data
        )

    all_payments = payment_service.fetch_payments_by_lease(
        db=test_db,
        lease_id=lease.id,
        current_user=operator_user
    )
    return all_payments, lease


@pytest.fixture
def pilot_tenant_safe_payments(test_db, payment_schema_factory, operator_user, pilot_active_lease):
    """
    Fixture to create multiple safe payments for a specific tenant's lease (fetched via tenant path).
    """
    lease = pilot_active_lease
    num_payments = 5

    already_paid = crud_payment.get_payments_aggregate_by_lease_id(test_db, lease_id=lease.id)
    remaining_balance = lease.agreed_rent_amt - already_paid
    amount_per_payment = remaining_balance // num_payments

    for _ in range(num_payments):
        payment_data = payment_schema_factory(
            amount_paid=amount_per_payment,
            lease_id=lease.id
        )
        payment_service.add_payment_record(
            db=test_db,
            current_user=operator_user,
            payment_data=payment_data
        )

    tenant_payments = payment_service.fetch_tenant_lease_payments(
        db=test_db,
        lease_id=lease.id,
        tenant_id=lease.tenant_id,
        skip=None,
        limit=None
    )
    return tenant_payments, lease
