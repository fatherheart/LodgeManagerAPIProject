import pytest
from app.crud.crud_lodge_operator import crud_lodge_operator
from app.models import Lodge
from app.schemas import lodge as schema_lodge
from app.schemas.lodge import RoomGenerator
from app.services import lodge_service


@pytest.fixture
def lodge_schema_factory():
    """
    A pytest fixture that provides a factory for creating lodge schemas.
    """
    def _create(
        name: str = 'Lodge Test',
        address: str = 'Test Address'
    ):
        return schema_lodge.LodgeCreate(
            name=name, address=address
        )
    return _create


@pytest.fixture
def mock_lodge_schema(lodge_schema_factory):
    """
    A pytest fixture that provides a mock lodge schema.
    """
    return lodge_schema_factory()


@pytest.fixture
def mock_update_lodge_schema():
    """
    A pytest fixture that provides a mock lodge update schema.
    """
    return schema_lodge.LodgeUpdate(
        name='A Lodge',
        address='A Address'
    )


@pytest.fixture
def lodge_schema_with_room_generator_factory():
    def _create(
        name: str = 'Lodge Test',
        address: str = 'Test Address',
        default_rent: int = 250000,
        prefix: str = '',
        start_number: int = 1,
        end_number: int = 5
    ):
        room_gen = RoomGenerator(
            prefix=prefix,
            start_number=start_number,
            end_number=end_number,
            default_rent=default_rent,
            default_description='Test description'
        )
        return schema_lodge.LodgeCreate(
            name=name,
            address=address,
            room_generator=room_gen
        )
    return _create


@pytest.fixture
def operator_pilot_lodge(test_db, operator_user, mock_lodge_schema):
    """
    A pytest fixture that creates an unclaimed pilot lodge by an operator.
    """
    return lodge_service.create_new_lodge_for_authorized_user(
        db=test_db,
        current_user=operator_user,
        lodge_data=mock_lodge_schema
    )


@pytest.fixture
def landlord_claimed_lodge(test_db, landlord_user, mock_lodge_schema):
    """
    A pytest fixture that adds a pure claimed lodge to the database for a landlord (legal title only).
    """
    return lodge_service.create_new_lodge_for_authorized_user(
        test_db,
        current_user=landlord_user,
        lodge_data=mock_lodge_schema
    )


@pytest.fixture
def other_landlord_lodge(test_db, other_landlord_user, lodge_schema_factory):
    """
    A pytest fixture that adds a lodge for a different landlord to the database.
    """
    lodge_schema = lodge_schema_factory(name='Lodge A', address='Address A')
    return lodge_service.create_new_lodge_for_authorized_user(
        test_db,
        current_user=other_landlord_user,
        lodge_data=lodge_schema
    )


@pytest.fixture
def hired_caretaker_claimed_lodge(test_db, landlord_claimed_lodge, operator_user):
    """
    A pytest fixture that provides a claimed landlord lodge with an active assigned caretaker.
    """
    crud_lodge_operator.assign_operator(
        test_db,
        lodge_id=landlord_claimed_lodge.id,
        operator_id=operator_user.id
    )
    return landlord_claimed_lodge


@pytest.fixture
def assign_other_operator_to_other_lodge(test_db, other_operator_user, other_landlord_lodge):
    """
    Assigns secondary caretaker to secondary landlord lodge.
    """
    return crud_lodge_operator.assign_operator(
        test_db,
        operator_id=other_operator_user.id,
        lodge_id=other_landlord_lodge.id
    )


@pytest.fixture
def landlord_portfolio_lodges(test_db, landlord_user, lodge_schema_factory):
    """
    A pytest fixture that adds multiple lodges to the database for landlord portfolio tests.
    """
    db_lodges: list[Lodge] = []
    for i in range(4):
        lodge_schema = lodge_schema_factory(name=f'Lodge {i + 1}', address=f'Address {i + 1}')
        new_lodge = lodge_service.create_new_lodge_for_authorized_user(
            test_db,
            current_user=landlord_user,
            lodge_data=lodge_schema
        )
        db_lodges.append(new_lodge)

    return db_lodges
