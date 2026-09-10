# Mock Frontend — LodgeOps Prototype Wireframes

This folder contains static HTML/CSS/JavaScript wireframes for the LodgeOps interface. They are **not the production frontend** — that lives in `../frontend/`. These are high-fidelity prototypes used for rapid UI iteration, manual API testing, and design sign-off without needing to run the React build pipeline.

---

## How They Work

When the FastAPI backend starts, [`app/main.py`](../backend/app/main.py) automatically detects this folder and mounts it as a static file server at the `/mock` path:

```
http://localhost:8000/mock/<filename>.html
```

**No build step. No npm. No compilation.** Open the URL while the backend is running and the page loads instantly.

The JS in `js/api.js` makes real HTTP requests to `http://localhost:8000/api/v1/*` using the same cookies the backend sets on login — so these pages test the live API end-to-end.

---

## Prerequisites

1. The backend must be running at `http://localhost:8000`. See [`backend/README.md`](../backend/README.md) for setup.
2. A browser (Chrome, Firefox, Edge).

---

## Available Screens

| URL | Screen | Role |
|---|---|---|
| [`/mock/login.html`](http://localhost:8000/mock/login.html) | Login | All |
| [`/mock/register.html`](http://localhost:8000/mock/register.html) | Landlord registration | Public |
| [`/mock/tenant-register.html`](http://localhost:8000/mock/tenant-register.html) | Tenant registration (via invite) | Public |
| [`/mock/dashboard.html`](http://localhost:8000/mock/dashboard.html) | Landlord main dashboard (financials, room grid) | Landlord |
| [`/mock/lodges.html`](http://localhost:8000/mock/lodges.html) | Lodge portfolio | Landlord |
| [`/mock/rooms.html`](http://localhost:8000/mock/rooms.html) | Room inventory and status management | Landlord |
| [`/mock/tenants.html`](http://localhost:8000/mock/tenants.html) | Tenant directory | Landlord |
| [`/mock/tenant-approvals.html`](http://localhost:8000/mock/tenant-approvals.html) | Pending tenant approval triage | Landlord |
| [`/mock/leases.html`](http://localhost:8000/mock/leases.html) | Lease management | Landlord |
| [`/mock/payments.html`](http://localhost:8000/mock/payments.html) | Payment recording and history | Landlord |
| [`/mock/tenant-dashboard.html`](http://localhost:8000/mock/tenant-dashboard.html) | Tenant resident portal | Tenant |
| [`/mock/tenant-leases.html`](http://localhost:8000/mock/tenant-leases.html) | Tenant lease history | Tenant |
| [`/mock/tenant-payments.html`](http://localhost:8000/mock/tenant-payments.html) | Tenant payment history | Tenant |
| [`/mock/tenant-profile.html`](http://localhost:8000/mock/tenant-profile.html) | Tenant profile management | Tenant |
| [`/mock/tenant-onboarding.html`](http://localhost:8000/mock/tenant-onboarding.html) | Tenant onboarding flow | Tenant |
| [`/mock/tenant-pending.html`](http://localhost:8000/mock/tenant-pending.html) | Tenant approval pending screen | Tenant |

---

## File Structure

```
mock_frontend/
├── css/                    # Shared stylesheet(s)
├── js/
│   ├── api.js              # Axios wrapper: auth headers, base URL, request helpers
│   └── dashboard.js        # Dashboard-specific JS (chart rendering, badge logic)
├── img/                    # Static image assets
├── dashboard.html
├── lodges.html
├── rooms.html
├── tenants.html
├── tenant-approvals.html
├── leases.html
├── payments.html
├── login.html
├── register.html
├── tenant-register.html
├── tenant-dashboard.html
├── tenant-leases.html
├── tenant-payments.html
├── tenant-profile.html
├── tenant-onboarding.html
└── tenant-pending.html
```

---

## Important Notes

- These wireframes are **not deployed to production**. They are served locally only.
- They interact with the **live API** using real data from the local SQLite database.
- Do not use these for performance or load testing — they have no caching layer.
- When the production React frontend (`../frontend/`) reaches feature parity with a screen, the corresponding wireframe becomes obsolete.
