from fastapi import FastAPI
from app.core.config import settings, PROJECT_ROOT
from app.api.v1.user import router as user_router
from app.api.v1.lodges import router as lodge_router
from app.api.v1.rooms import router as room_router
from app.api.v1.tenants import router as tenant_router
from app.api.v1.leases import router as lease_router
from app.api.v1.payments import router as payment_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.handlers import lodge_ops_handlers
from app.api.v1.dashboards.landlord_dashboard import router as operator_dashboard_router
from app.api.v1.dashboards.tenant_dashboard import router as tenant_dashboard_router
from app.api.v1.invites import router as invite_router

tags_metadata = [
    {
        "name": "Authentication",
        "description": "Operations for user registration, login, and token management.",
    },
    {
        "name": "Lodges",
        "description": "Manage lodges (properties). Operators and landlords can create and configure their lodges.",
    },
    {
        "name": "Rooms",
        "description": "Manage rooms within lodges. Operators can add rooms and update room status and pricing.",
    },
    {
        "name": "Tenants",
        "description": "Operations for tenant management, profile updates, and tenant retrieval.",
    },
    {
        "name": "Leases",
        "description": "Manage lease agreements between operators and tenants.",
    },
    {
        "name": "Payments",
        "description": "Handle rent payments and payment tracking for leases.",
    },
    {
        "name": "Dashboards",
        "description": "Retrieve aggregated statistics and metrics for operator and tenant dashboards.",
    },
    {
        "name": "Invites",
        "description": "Manage invitations sent by operators to prospective tenants.",
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME, 
    description="LodgeOps - Comprehensive Lodge Management System API.",
    version="1.0.0",
    contact={
        "name": "DonaldXoftDev",
        "url": "https://github.com/DonaldXoftDev",
    },
    openapi_tags=tags_metadata,
    exception_handlers=lodge_ops_handlers
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.final_cors_origins, #allowed app origins for interacting with the backend
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(user_router, prefix='/api/v1/auth', tags=['Authentication'])

app.include_router(lodge_router, prefix='/api/v1/lodges', tags=['Lodges'])

app.include_router(room_router, prefix='/api/v1/rooms', tags=['Rooms'])

app.include_router(tenant_router, prefix='/api/v1/tenants', tags=['Tenants'])

app.include_router(lease_router, prefix='/api/v1/leases', tags=['Leases'])


app.include_router(payment_router, prefix='/api/v1/payments', tags=['Payments'])


app.include_router(operator_dashboard_router, prefix='/api/v1/dashboard-landlord', tags=['Dashboards'])
app.include_router(tenant_dashboard_router, prefix='/api/v1/dashboard-tenant', tags=['Dashboards'])


app.include_router(invite_router, prefix='/api/v1/invites', tags=['Invites'])

import os
from fastapi.staticfiles import StaticFiles

# Target mock_frontend in project root (parent of backend)
mock_frontend_path = os.path.join(os.path.dirname(PROJECT_ROOT), "mock_frontend")
if os.path.exists(mock_frontend_path):
    app.mount("/mock", StaticFiles(directory=mock_frontend_path, html=True), name="mock")

@app.get("/healthy")
def health_status():
    return {"message": f"Your {settings.PROJECT_NAME} is working well"}




