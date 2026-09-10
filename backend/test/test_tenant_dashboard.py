import pytest
from fastapi import status

from app.core.enums import BadgeTexts, BadgeVariants
from test.conftest import base_url

tenant_dashboard_url = f'{base_url}/dashboard-tenant'


def test_tenant_get_dashboard_stats_returns_200(
    auth_client_factory, pilot_active_lease
):
    client = auth_client_factory(user_id=pilot_active_lease.tenant.user_id)
    response = client.get(f'{tenant_dashboard_url}/me/tenants')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(data, list)
    assert 'room' in data[0]
    assert 'lease' in data[0]
    assert 'finance' in data[0]
    assert 'badge_text' in data[0]
    assert 'badge_variant' in data[0]


def test_tenant_get_dashboard_stat_no_lease_returns_200(
    authenticated_tenant_client
):
    response = authenticated_tenant_client.get(f'{tenant_dashboard_url}/me/tenants')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data == []


def test_operator_cannot_get_tenant_dashboard_stat_returns_403(
    authenticated_operator_client
):
    response = authenticated_operator_client.get(f'{tenant_dashboard_url}/me/tenants')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only tenants are allowed.'


@pytest.mark.parametrize('fixture_name, expected_badge_text, expected_badge_variant', [
    ('pilot_active_lease', BadgeTexts.OWING, BadgeVariants.DANGER),
    ('pilot_tenant_safe_payments', BadgeTexts.SAFE, BadgeVariants.SUCCESS)
])
def test_tenant_dashboard_stat_gives_valid_badge(
    auth_client_factory, fixture_name, request, expected_badge_text, expected_badge_variant
):
    val = request.getfixturevalue(fixture_name)
    lease = val[1] if isinstance(val, tuple) else val
    client = auth_client_factory(user_id=lease.tenant.user_id)

    response = client.get(f'{tenant_dashboard_url}/me/tenants')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data != []
    assert data[0]['badge_text'] == expected_badge_text.value
    assert data[0]['badge_variant'] == expected_badge_variant.value