import pytest
from app.core.enums import UserRole
from app.schemas import user as schema_user
from app.services import user_service


@pytest.fixture
def user_schema_factory():
    def _create(
        first_name: str = 'User',
        last_name: str = 'Test',
        email: str = 'user@test.com',
        password: str = 'User12345',
        phone_no: str = '08108417160'
    ):
        return schema_user.UserCreate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            phone_no=phone_no
        )
    return _create


@pytest.fixture
def landlord_schema_factory(user_schema_factory):
    """
    A pytest fixture that provides a factory for creating landlord schemas.
    """
    def _create(**kwargs):
        defaults = {
            "first_name": 'Landlord A',
            "last_name": 'owner',
            "email": 'landlord@test.com',
            "password": 'Landlord12345',
            "phone_no": '08108417160'
        }
        defaults.update(kwargs)
        return user_schema_factory(**defaults)
    return _create


@pytest.fixture
def operator_schema_factory(user_schema_factory):
    """
    A pytest fixture that provides a factory for creating operator schemas.
    """
    def _create(**kwargs):
        defaults = {
            "first_name": 'Operator',
            "last_name": 'Test',
            "email": 'operator@test.com',
            "password": 'Operator12345',
            "phone_no": '081084484802'
        }
        defaults.update(kwargs)
        return user_schema_factory(**defaults)
    return _create


@pytest.fixture
def mock_landlord_schema(landlord_schema_factory):
    """
    A pytest fixture that provides a mock landlord schema.
    """
    return landlord_schema_factory()


@pytest.fixture
def mock_operator_schema(operator_schema_factory):
    """
    A pytest fixture that provides a mock operator schema.
    """
    return operator_schema_factory()


@pytest.fixture
def create_user_in_db(test_db):
    def _create(schema: schema_user.UserCreate, role: UserRole):
        from app.core.security import get_password_hash
        from app.crud.user import crud_user

        hashed = get_password_hash(schema.password)
        base_user_data = schema_user.UserInternal(
            **schema.model_dump(exclude={'password'}),
            hashed_password=hashed,
            role=role
        )
        return crud_user.create(test_db, obj_in=base_user_data)
    return _create


@pytest.fixture
def landlord_user(mock_landlord_schema, create_user_in_db):
    """
    A pytest fixture that adds a landlord (Chief Ade) to the database.
    """
    return create_user_in_db(mock_landlord_schema, role=UserRole.LANDLORD)


@pytest.fixture
def other_landlord_user(landlord_schema_factory, create_user_in_db):
    """
    A pytest fixture that adds a secondary landlord to the database for isolation tests.
    """
    new_l_schema = landlord_schema_factory(
        first_name='Landlord',
        last_name='B',
        email='landlordb@test.com',
        password='Landlordb12345',
        phone_no='091580380375'
    )
    return create_user_in_db(new_l_schema, role=UserRole.LANDLORD)


@pytest.fixture
def operator_user(test_db, mock_operator_schema):
    """
    A pytest fixture that adds a primary pilot caretaker (Musa) to the database.
    """
    return user_service.sign_up_operator(test_db, operator_data=mock_operator_schema)


@pytest.fixture
def other_operator_user(test_db, operator_schema_factory):
    """
    A pytest fixture that adds a secondary caretaker (Ibrahim) to the database.
    """
    new_operator = operator_schema_factory(
        first_name='Operator B',
        email='operatorb2@gmail.com',
        phone_no='081084484899'
    )
    return user_service.sign_up_operator(test_db, operator_data=new_operator)


@pytest.fixture
def auth_client_factory(client, test_db):
    """
    A pytest fixture that provides a factory for creating authenticated clients.
    """
    def _authenticate(user_id: int):
        from test.test_auth import auth_url_base
        from app.core import security
        from app.crud.user import crud_user
        from app.schemas.refresh_token import RefreshTokenInternal

        access_token = security.create_access_token(subject=str(user_id))
        refresh_token = security.create_refresh_token(subject=str(user_id))

        refresh_token_schema = RefreshTokenInternal(user_id=user_id, token=refresh_token)
        crud_user.create_new_refresh_token_record(test_db, refresh_in=refresh_token_schema)

        client.cookies.set(name='access_token', value=access_token, path='/')
        client.cookies.set(name='refresh_token', value=refresh_token, path=f'{auth_url_base}')

        return client

    return _authenticate


@pytest.fixture
def authenticated_landlord_client(auth_client_factory, landlord_user):
    """
    A pytest fixture that provides an authenticated client for a landlord.
    """
    client = auth_client_factory(user_id=landlord_user.id)
    client.user = landlord_user
    return client


@pytest.fixture
def authenticated_operator_client(auth_client_factory, operator_user):
    """
    A pytest fixture that provides an authenticated client for an operator.
    """
    client = auth_client_factory(user_id=operator_user.id)
    client.user = operator_user
    return client
