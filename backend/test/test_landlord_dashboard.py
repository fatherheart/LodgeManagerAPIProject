import json
import pytest
from fastapi import status

from app.core.enums import BadgeTexts, RoomStatus
from test.conftest import base_url

landlord_dashboard_url = f'{base_url}/dashboard-landlord'


# =========================================================================
# 1. OPERATOR LODGE DASHBOARD METRICS (STRICT AAA & RICH DATA)
# =========================================================================

def test_operator_dashboard_stats_paginated_returns_200(
    authenticated_operator_client, pilot_dashboard_metrics_data
):
    """
    Tests that the dashboard successfully returns metrics for an active operator.
    Verifies that all expected keys (financials, entity_counts, room grids) are present.
    """
    lodge_id, db_stats = pilot_dashboard_metrics_data

    response = authenticated_operator_client.get(url=f'{landlord_dashboard_url}/me/landlord/{lodge_id}')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert 'financials' in data
    assert 'entity_counts' in data
    assert 'occupied_rooms_lease' in data
    assert 'maintenance_rooms' in data
    assert 'vacant_rooms' in data

    assert len(data['vacant_rooms']) == 3
    assert len(data['maintenance_rooms']) == 3
    assert len(data['occupied_rooms_lease']['safe']) == 3
    assert len(data['occupied_rooms_lease']['expiring']) == 3
    assert len(data['occupied_rooms_lease']['overdue']) == 3
    assert len(data['occupied_rooms_lease']['pending_moveout']) == 3
    assert len(data['occupied_rooms_lease']['owing']) == 4

    assert data['entity_counts']['room_status_counts']['occupied'] == 15
    assert data['entity_counts']['room_status_counts']['vacant'] == 3
    assert data['entity_counts']['room_status_counts']['maintenance'] == 3

    assert data['entity_counts']['occupied_counts']['safe'] == 3
    assert data['entity_counts']['occupied_counts']['expiring'] == 3
    assert data['entity_counts']['occupied_counts']['overdue'] == 3
    assert data['entity_counts']['occupied_counts']['pending_moveout'] == 3
    assert data['entity_counts']['occupied_counts']['owing'] == 4


def test_operator_dashboard_pagination_skip_returns_200(
    authenticated_operator_client, pilot_dashboard_metrics_data
):
    lodge_id, db_stats = pilot_dashboard_metrics_data

    response = authenticated_operator_client.get(url=f'{landlord_dashboard_url}/me/landlord/{lodge_id}?skip=2')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK


def test_operator_dashboard_pagination_limit_returns_200(
    authenticated_operator_client, pilot_dashboard_metrics_data
):
    lodge_id, db_stats = pilot_dashboard_metrics_data

    response = authenticated_operator_client.get(url=f'{landlord_dashboard_url}/me/landlord/{lodge_id}?limit=1')
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    total_rooms_in_arrays = (
        len(data['occupied_rooms_lease']['safe']) +
        len(data['occupied_rooms_lease']['expiring']) +
        len(data['occupied_rooms_lease']['overdue']) +
        len(data['occupied_rooms_lease']['pending_moveout']) +
        len(data['occupied_rooms_lease']['owing']) +
        len(data['vacant_rooms']) +
        len(data['maintenance_rooms'])
    )
    assert total_rooms_in_arrays <= 1


def test_operator_dashboard_pagination_exceed_limit_returns_200(
    authenticated_operator_client, pilot_dashboard_metrics_data
):
    lodge_id, db_stats = pilot_dashboard_metrics_data

    response = authenticated_operator_client.get(url=f'{landlord_dashboard_url}/me/landlord/{lodge_id}?limit=1000')

    assert response.status_code == status.HTTP_200_OK


# =========================================================================
# 2. DASHBOARD FILTERING SCENARIOS (PARAMETRIZED)
# =========================================================================

@pytest.mark.parametrize("filter_param, filter_value, expected_key", [
    ("room_statuses", RoomStatus.VACANT.value, "vacant_rooms"),
    ("room_statuses", RoomStatus.MAINTENANCE.value, "maintenance_rooms"),
])
def test_operator_dashboard_room_status_filter_returns_200(
    authenticated_operator_client, pilot_dashboard_metrics_data, filter_param, filter_value, expected_key
):
    lodge_id, db_stats = pilot_dashboard_metrics_data

    response = authenticated_operator_client.get(
        url=f'{landlord_dashboard_url}/me/landlord/{lodge_id}?{filter_param}={filter_value}'
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(data[expected_key]) == 3


@pytest.mark.parametrize("badge_filter, expected_count", [
    (BadgeTexts.SAFE, 3),
    (BadgeTexts.EXPIRING, 3),
    (BadgeTexts.OVERDUE, 3),
    (BadgeTexts.PENDING_MOVEOUT, 3),
    (BadgeTexts.OWING, 4),
])
def test_operator_dashboard_financial_filter_returns_200(
    authenticated_operator_client, pilot_dashboard_metrics_data, badge_filter, expected_count
):
    lodge_id, db_stats = pilot_dashboard_metrics_data

    response = authenticated_operator_client.get(
        url=f'{landlord_dashboard_url}/me/landlord/{lodge_id}?financial_filters={badge_filter.value}'
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK

    filter_key = badge_filter.value.lower()
    assert len(data['occupied_rooms_lease'][filter_key]) == expected_count


# =========================================================================
# 3. AUTHORIZATION & CROSS-LODGE PROTECTIONS
# =========================================================================

def test_unassigned_operator_dashboard_returns_404(
    authenticated_operator_client, other_landlord_lodge
):
    response = authenticated_operator_client.get(
        url=f'{landlord_dashboard_url}/me/landlord/{other_landlord_lodge.id}'
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lodge could not be found'


def test_tenant_cannot_access_lodge_dashboard_returns_403(
    authenticated_tenant_client, operator_pilot_lodge
):
    response = authenticated_tenant_client.get(
        url=f'{landlord_dashboard_url}/me/landlord/{operator_pilot_lodge.id}'
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'


# =========================================================================
# 4. ROOM LEASE INFO MODAL (GET /dashboard-landlord/lease-info/{lease_id})
# =========================================================================

def test_operator_get_room_lease_info_returns_200(
    authenticated_operator_client, pilot_active_lease
):
    response = authenticated_operator_client.get(
        url=f'{landlord_dashboard_url}/lease-info/{pilot_active_lease.id}'
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert 'room' in data
    assert 'lease' in data
    assert 'tenant' in data
    assert 'finance' in data
    assert 'badge_text' in data
    assert 'badge_variant' in data


def test_operator_get_room_lease_info_non_existent_returns_404(
    authenticated_operator_client
):
    response = authenticated_operator_client.get(
        url=f'{landlord_dashboard_url}/lease-info/99999'
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lease could not be found'


def test_unassigned_operator_get_room_lease_info_returns_404(
    authenticated_operator_client, other_landlord_active_lease
):
    response = authenticated_operator_client.get(
        url=f'{landlord_dashboard_url}/lease-info/{other_landlord_active_lease.id}'
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()['detail'] == 'Lodge could not be found'


def test_tenant_cannot_get_room_lease_info_returns_403(
    authenticated_tenant_client, pilot_active_lease
):
    response = authenticated_tenant_client.get(
        url=f'{landlord_dashboard_url}/lease-info/{pilot_active_lease.id}'
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()['detail'] == 'Only operators or landlords are allowed.'

