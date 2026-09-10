"""
Root pytest configuration for LodgeOps backend integration tests.
Sets up SQLite in-memory engine, transaction isolation, TestClient, and loads domain fixtures.
"""
import pytest
from passlib.context import CryptContext
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.core import security
from app.db.session import Base
from app.main import app

# =========================================================================
# 🔌 DOMAIN FIXTURE PLUGINS
# =========================================================================
pytest_plugins = [
    "test.fixtures.auth_fixtures",
    "test.fixtures.lodge_fixtures",
    "test.fixtures.room_fixtures",
    "test.fixtures.tenant_fixtures",
    "test.fixtures.lease_fixtures",
    "test.fixtures.payment_fixtures",
    "test.fixtures.dashboard_fixtures",
    "test.fixtures.ownership_invite_fixtures",
    "test.fixtures.operator_invite_fixtures",
]



# =========================================================================
# 🗄️ DATABASE ENGINE & SESSION CONFIGURATION
# =========================================================================
SQLALCHEMY_DATABASE_URL = 'sqlite:///:memory:'

engine = create_engine(
    url=SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False},
    poolclass=StaticPool
)

TestSessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

base_url = "/api/v1"


@pytest.fixture(scope='session', autouse=True)
def test_session():
    """
    Session-scoped fixture: creates all database tables at suite startup and drops them on teardown.
    """
    try:
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db():
    """
    Function-scoped fixture: wraps each test in an isolated database transaction with rollback.
    """
    with engine.connect() as conn:
        txn = conn.begin()
        session = TestSessionLocal(bind=conn)
        try:
            yield session
        finally:
            txn.rollback()


@pytest.fixture(scope='session', autouse=True)
def fast_pwd_context():
    """
    Session-scoped monkeypatch: reduces bcrypt rounds to 2 for instant password hashing during tests.
    """
    mp = pytest.MonkeyPatch()
    fast_context = CryptContext(schemes=['bcrypt'], deprecated='auto', bcrypt__rounds=2)
    mp.setattr(security, 'pwd_context', fast_context)
    yield
    mp.undo()


@pytest.fixture
def client(test_db):
    """
    Function-scoped fixture: provides a FastAPI TestClient bound to the isolated test database.
    """
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c
