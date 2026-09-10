# Backend — LodgeOps API

FastAPI backend for the LodgeOps property management system.

> For a full project overview, architecture, and quick-start guide, see the [root README](../README.md).

---

## 📋 Table of Contents

- [Tech Stack](#-tech-stack)
- [Backend Architecture](#-backend-architecture)
- [Domain Model](#-domain-model)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Local Setup](#-local-setup)
- [Running Tests](#-running-tests)
- [Contributing](#-contributing)

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Python 3.11+, FastAPI |
| **ORM** | SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Validation** | Pydantic v2 |
| **Auth** | PyJWT, Passlib + Bcrypt 4.0.1, HTTP-only Cookie sessions |
| **Database** | SQLite (Development) / PostgreSQL-ready (Production) |
| **Testing** | Pytest, pytest-cov, HTTPX |

---

## 🏗 Backend Architecture

Every request passes through exactly these layers in order. No layer may skip another.

```
HTTP Request
     │
     ▼
┌──────────────────────────────────────┐
│  Presentation  (app/api/v1/)         │
│  FastAPI Routers + Dependency        │
│  Injection. No SQL. No business      │
│  logic.                              │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Business Logic  (app/services/)     │
│  Domain rules, workflow              │
│  orchestration. No HTTP objects.     │
│  No raw SQL.                         │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Data Access  (app/crud/)            │
│  SQLAlchemy queries, aggregations,   │
│  and joins. No business logic.       │
└──────────────┬───────────────────────┘
               │
     ┌─────────┴──────────┐
     ▼                    ▼
┌──────────┐     ┌──────────────────┐
│  Models  │     │  Schemas         │
│ (ORM +   │     │  (Pydantic v2    │
│ @property│     │  Create/Update/  │
│ + cascade│     │  Response DTOs)  │
└────┬─────┘     └──────────────────┘
     │
     ▼
  Database
```

**Key design rules:**
- Lease `status` is stored as `NULL` (Active/Overdue), `Pending_Termination`, or `Terminated`. Never compute and store `Active`/`Overdue` — those are derived at runtime via `@property computed_status`.
- Payment ledger is **append-only**. Balances and totals are computed via `func.sum` + `outerjoin` at the database level, never by looping over ORM objects in Python.
- Tenant data isolation: every landlord-scoped query filters by `landlord_id`. A landlord can never read or mutate another landlord's data.

---

## 🗄 Domain Model

| Entity | Table | Purpose |
|---|---|---|
| **User** | `users` | Core identity for Landlords and Tenants (email, hashed password, role). |
| **RefreshToken** | `refresh_tokens` | Whitelist of active refresh tokens. Rotation and revocation on logout. |
| **Invitation** | `invitations` | UUID invite links scoped to a Lodge with an expiry timestamp. |
| **Lodge** | `lodges` | A physical property owned by a Landlord. Parent of Rooms and TenantProfiles. |
| **Room** | `rooms` | A rentable unit within a Lodge. Tracks `room_status` and `base_rent_price`. |
| **TenantProfile** | `tenant_profiles` | Extended profile: Student Level, Department, Emergency Contacts, Approval Status. |
| **Lease** | `leases` | Rental contract linking a Tenant to a Room. Status column is `NULL` (active/overdue), `Pending_Termination`, or `Terminated`. |
| **Payment** | `payments` | Append-only rent payment ledger. |

**Cascade rule:** Deleting a `Lodge` cascades via `ondelete='CASCADE'` (DB) and `cascade='all, delete-orphan'` (ORM) to all its Rooms, TenantProfiles, and Invitations.

---

## 📡 API Reference

> For the full API specification, Layer-by-Layer Code Audit, and System Flow, see the **[LODGEOPS_MASTER_SPEC.md](../LODGEOPS_MASTER_SPEC.md)** in the project root.

Interactive documentation is available at http://localhost:8000/docs once the server is running.

---

## 📁 Project Structure

```
backend/
├── alembic/                    # Versioned database migration scripts
│   └── versions/
├── app/
│   ├── main.py                 # App entry point: routers, middleware, CORS
│   ├── api/
│   │   ├── deps.py             # FastAPI dependencies (auth, role guards, DB session)
│   │   └── v1/
│   │       ├── user.py         # /api/v1/auth
│   │       ├── lodges.py       # /api/v1/lodges
│   │       ├── rooms.py        # /api/v1/rooms
│   │       ├── tenants.py      # /api/v1/tenants
│   │       ├── leases.py       # /api/v1/leases
│   │       ├── payments.py     # /api/v1/payments
│   │       ├── invites.py      # /api/v1/invites
│   │       └── dashboards/
│   │           ├── landlord_dashboard.py
│   │           └── tenant_dashboard.py
│   ├── core/
│   │   ├── config.py           # Pydantic Settings — reads from .env
│   │   ├── enums.py            # Domain enums (UserRole, RoomStatus, LeaseStatus…)
│   │   ├── exceptions.py       # Custom domain exception classes
│   │   ├── handlers.py         # Global FastAPI exception handlers
│   │   └── security.py         # Bcrypt hashing and JWT creation
│   ├── crud/                   # SQLAlchemy repository layer
│   │   ├── base_crud.py, user.py, lodge.py, room.py
│   │   └── tenantprofile.py, lease.py, payment.py, invite.py
│   ├── db/
│   │   ├── base.py             # SQLAlchemy Base model registry
│   │   └── session.py          # Engine, SessionLocal, and pragma setup
│   ├── models/                 # ORM entity definitions
│   │   └── user.py, refresh_token.py, invitation.py, lodge.py,
│   │       room.py, tenantprofile.py, lease.py, payment.py
│   ├── schemas/                # Pydantic v2 DTOs (Create / Update / Response)
│   │   └── user.py, invitation.py, lodge.py, room.py, tenantprofile.py,
│   │       lease.py, payment.py, dashboard.py, financial.py, error.py,
│   │       entity_count.py, generic_extras.py, refresh_token.py
│   └── services/               # Business logic layer
│       └── user_service.py, invite_service.py, lodge_service.py,
│           room_service.py, tenant_services.py, lease_services.py,
│           payment_service.py, dashboard_service.py
├── test/
│   ├── conftest.py             # Fixtures, in-memory SQLite test DB, auth helpers
│   ├── test_auth.py
│   ├── test_lodge.py
│   ├── test_room.py
│   ├── test_tenant.py
│   ├── test_lease.py
│   ├── test_payment.py
│   ├── test_invite.py
│   ├── test_landlord_dashboard.py
│   ├── test_tenant_dashboard.py
│   ├── test_main.py
│   └── test_example.py
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── System_Flow.md              # API user flow reference
```

---

## 🚀 Local Setup

> ⚠️ All commands assume your terminal starts at the **project root** (`LodgeOpsProject/`).

### 1. Navigate and create the virtual environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Your terminal prompt should show `(.venv)` when active.

### 2. Configure environment variables

Create `backend/.env` manually (there is no `.env.example` yet — one will be added in a future commit):

```ini
# Core
PROJECT_NAME="LodgeOps"
DATABASE_URL="sqlite:///./lodge_manager.db"

# JWT — generate keys with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY="your-access-token-secret-here"
REFRESH_SECRET_KEY="your-refresh-token-secret-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS — DEBUG=true merges CORS_ORIGINS and DEV_CORS_ORIGINS
DEBUG=true
CORS_ORIGINS="http://localhost:5173"
DEV_CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:3000"
```

> ⚠️ Never commit `.env`. It is in `.gitignore`.

### 3. Run database migrations

```powershell
# Must be inside backend/ with (.venv) active
alembic upgrade head
```

Creates `backend/lodge_manager.db`.

### 4. Start the server

```powershell
uvicorn app.main:app --reload --port 8000
```

| URL | Purpose |
|---|---|
| `http://localhost:8000/docs` | Swagger UI — interactive API explorer |
| `http://localhost:8000/redoc` | ReDoc API documentation |
| `http://localhost:8000/healthy` | Health check |
| `http://localhost:8000/mock/dashboard.html` | Prototype wireframes |

---

## 🧪 Running Tests

The test suite uses an isolated in-memory SQLite database. [`pytest.ini`](pytest.ini) pre-configures `testpaths`, verbosity, coverage source, and warnings — so from inside `backend/` with the venv active, you only need:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

That's it. The `.ini` file handles the rest:
- `testpaths = test` → discovers `backend/test/` automatically
- `addopts` → injects `-v -s --cov=app --cov-report=term-missing` on every run

> ✅ Expected: **157 passed**, ~41 seconds, **95%+ coverage**.

---

## 🤝 Contributing

1. Routers handle HTTP only. No business logic in endpoint functions.
2. Services handle domain rules only. No `Request`/`Response` objects, no raw SQL.
3. CRUD handles SQLAlchemy queries only. No `if` branches for business rules.
4. All tests must pass before committing.
