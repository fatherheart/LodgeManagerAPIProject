# LodgeOps — Residential Lodge Management System

> A full-stack platform for managing student accommodation: tenant onboarding, room inventory, lease contracts, rent tracking, and operational dashboards.

---

## 📖 What is LodgeOps?

LodgeOps is a property management system built for landlords managing student lodges. It digitises the full operational lifecycle:

1. **Landlord** registers a lodge and its rooms, then issues invite links to prospective tenants.
2. **Tenant** registers via the invite link, submits their profile, and waits for approval.
3. **Landlord** approves the tenant, creates a lease, and records rent payments. *(A dedicated Caretaker role is on the roadmap for on-site operations.)*
4. Both parties access personalised dashboards showing their lease status, room health, and financial position.

---

## 🗂 Monorepo Structure

```
LodgeOpsProject/
├── backend/                 # FastAPI REST API (Python 3.11+)
├── frontend/                # React 18 + TypeScript + Vite SPA
├── mock_frontend/           # Static HTML/CSS/JS prototype wireframes
├── openapi.json             # Exported OpenAPI schema snapshot
└── README.md                # ← You are here
```

---

## 🏛 System Architecture

The system is split into three independently deployable layers:

```
┌──────────────────────┐     HTTP/JSON      ┌──────────────────────────┐
│   React SPA          │ ──────────────────▶│   FastAPI Backend         │
│   (frontend/)        │ ◀────────────────── │   (backend/)              │
│   Port 5173          │                    │   Port 8000               │
└──────────────────────┘                    └────────────┬─────────────┘
                                                         │ SQLAlchemy ORM
                                                         ▼
                                            ┌──────────────────────────┐
                                            │   SQLite (Dev)           │
                                            │   PostgreSQL (Prod)      │
                                            └──────────────────────────┘
```

### User Roles

| Role | Responsibility |
|---|---|
| **Landlord** | Creates lodges & rooms, issues invites, approves tenants, signs leases, records payments, views financial dashboards |
| **Caretaker** *(planned)* | On-site operations: screens tenants, manages room condition, triggers maintenance |
| **Tenant** | Registers via invite, manages profile, views lease, tracks payment history |

---

## ⚡ Quick Start

There are two ways to run LodgeOps locally depending on what you need:

---

### Option A — Backend Only (Wireframes included)

The backend alone is fully usable. When it starts, it automatically serves the HTML prototype screens from `mock_frontend/` at the `/mock` path — no separate frontend process required.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Create backend/.env and fill in values (see backend/README.md for all required keys)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Once running you have access to:
- `http://localhost:8000/docs` — Swagger API explorer
- `http://localhost:8000/mock/dashboard.html` — Landlord dashboard prototype
- `http://localhost:8000/mock/tenant-dashboard.html` — Tenant portal prototype

> See [`mock_frontend/README.md`](mock_frontend/README.md) for the full list of available screens.

---

### Option B — Backend + Frontend (Two terminals)

Use this when developing the React frontend. Both processes must run simultaneously.

**Terminal 1 — Backend:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm ci
npm run dev
```

The React app at `http://localhost:5173` is pre-configured to talk to the backend at `http://localhost:8000` via its Axios client.

> For environment variable configuration in both services, see [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md).


---

## 📚 Documentation Index

| Document | Purpose |
|---|---|
| [`backend/README.md`](backend/README.md) | Backend setup, environment variables, API reference, test commands |
| [`frontend/README.md`](frontend/README.md) | Frontend setup, npm scripts, component structure, troubleshooting |
| [`mock_frontend/README.md`](mock_frontend/README.md) | Prototype wireframes — what they are and how to access them |
| [`backend/System_Flow.md`](backend/System_Flow.md) | Source-of-truth for all API user flows |

---

## 🛠 Tech Stack Summary

| Layer | Technology |
|---|---|
| **Backend API** | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Frontend SPA** | React 18, TypeScript, Vite, Tailwind CSS, React Router |
| **Auth** | JWT (access + refresh), HTTP-only cookies, Bcrypt |
| **Database** | SQLite (development), PostgreSQL-ready (production) |
| **Testing** | Pytest, pytest-cov, HTTPX (157 tests, 95%+ coverage) |

---

## 🤝 Contributing

1. Backend: N-Tier pattern strictly enforced. Routers → Services → CRUD → Models. No skipping layers.
2. Frontend: Component-first. Pages only compose components; no raw API calls inside pages.
3. All tests must pass before any PR. From `backend/` with the venv active: `.\.venv\Scripts\python.exe -m pytest`
