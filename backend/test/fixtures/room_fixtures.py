import random
import pytest
from app.core.enums import RoomStatus
from app.crud.crud_lodge_operator import crud_lodge_operator
from app.models import Room
from app.schemas import room as schema_room
from app.services import room_service


@pytest.fixture
def room_schema_factory():
    """
    A pytest fixture that provides a factory for creating room schemas.
    """
    def _create(
        room_no: str = 'Test Rm-1',
        description: str = 'spacious self con',
        base_rent_price: int = 210000,
        lodge_id: int = 1
    ):
        return schema_room.RoomCreate(
            room_no=room_no,
            description=description,
            base_rent_price=base_rent_price,
            lodge_id=lodge_id
        )
    return _create


@pytest.fixture
def mock_room_schema(room_schema_factory, landlord_claimed_lodge):
    """
    A pytest fixture that provides a mock room schema bound to landlord's claimed lodge.
    """
    return room_schema_factory(lodge_id=landlord_claimed_lodge.id)


@pytest.fixture
def mock_update_room_schema():
    """
    A pytest fixture that provides a mock room update schema.
    """
    return schema_room.RoomUpdate(
        room_no='Rm-1 Test',
        description='Upstairs, 2nd floor',
        base_rent_price=400000,
        status=RoomStatus.MAINTENANCE
    )


@pytest.fixture
def pilot_room_schema(room_schema_factory, operator_pilot_lodge):
    """
    A pytest fixture that provides a room schema attached to the operator's pilot lodge.
    """
    return room_schema_factory(lodge_id=operator_pilot_lodge.id, room_no="Operator Rm 101")


@pytest.fixture
def pilot_lodge_room(test_db, pilot_room_schema, operator_user):
    """
    A pytest fixture that creates a room in the operator's pilot lodge.
    """
    return room_service.create_room_for_lodge(
        test_db,
        room_in=pilot_room_schema,
        current_user=operator_user
    )


@pytest.fixture
def hired_caretaker_room(test_db, hired_caretaker_claimed_lodge, operator_user, room_schema_factory):
    """
    A pytest fixture that provides a room in a claimed lodge operated by an assigned caretaker.
    """
    rm_schema = room_schema_factory(lodge_id=hired_caretaker_claimed_lodge.id, room_no="Assigned Rm 101")
    return room_service.create_room_for_lodge(
        test_db,
        room_in=rm_schema,
        current_user=operator_user
    )


@pytest.fixture
def other_landlord_room(test_db, room_schema_factory, other_landlord_lodge, other_landlord_user):
    """
    A pytest fixture that adds a room belonging to a different landlord.
    """
    crud_lodge_operator.assign_operator(
        test_db, lodge_id=other_landlord_lodge.id, operator_id=other_landlord_user.id
    )
    rm_schema = room_schema_factory(lodge_id=other_landlord_lodge.id)
    return room_service.create_room_for_lodge(
        test_db, current_user=other_landlord_user, room_in=rm_schema
    )


@pytest.fixture
def pilot_rooms_batch(test_db, room_schema_factory, operator_user, operator_pilot_lodge):
    """
    A pytest fixture that seeds 5 rooms in the operator's pilot lodge for listing & pagination tests.
    """
    db_rooms: list[Room] = []
    for i in range(5):
        rm_schema = room_schema_factory(
            lodge_id=operator_pilot_lodge.id,
            room_no=f"Pilot Rm {i + 1}",
            base_rent_price=250000 + (i * 10000)
        )
        room = room_service.create_room_for_lodge(
            test_db,
            room_in=rm_schema,
            current_user=operator_user
        )
        db_rooms.append(room)

    return db_rooms


@pytest.fixture
def pilot_vacant_rooms_pool(test_db, room_schema_factory, operator_user, operator_pilot_lodge):
    """
    A pytest fixture that seeds 20 vacant rooms in the operator's pilot lodge.
    """
    max_rooms = 20
    db_rooms = []
    for i in range(max_rooms):
        rm_schema = room_schema_factory(
            room_no=f'Test rm{i + 1}',
            description=f'description Test {i + 1}',
            base_rent_price=random.randint(250000, 350000),
            lodge_id=operator_pilot_lodge.id
        )
        new_room = room_service.create_room_for_lodge(
            test_db,
            current_user=operator_user,
            room_in=rm_schema
        )
        db_rooms.append(new_room)
    return db_rooms


@pytest.fixture
def pilot_maintenance_rooms_pool(test_db, room_schema_factory, operator_user, operator_pilot_lodge):
    """
    A pytest fixture that seeds 5 maintenance rooms in the operator's pilot lodge.
    """
    max_maintenance_rooms = 5
    db_maintenance_rooms = []
    for i in range(max_maintenance_rooms):
        room_data = room_schema_factory(
            room_no=f'maintenance room {i + 1}',
            lodge_id=operator_pilot_lodge.id
        )
        new_maintenance_room = room_service.create_room_for_lodge(
            test_db,
            room_in=room_data,
            current_user=operator_user
        )
        new_maintenance_room.status = RoomStatus.MAINTENANCE
        test_db.commit()
        test_db.refresh(new_maintenance_room)
        db_maintenance_rooms.append(new_maintenance_room)

    return db_maintenance_rooms
