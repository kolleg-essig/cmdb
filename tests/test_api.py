"""Tests für die REST-API: Authentifizierung, Asset-CRUD und Statistiken."""
import pytest


@pytest.fixture
def api_headers(test_user):
    """Liefert den X-API-Key-Header des Test-Users."""
    return {"X-API-Key": test_user.api_key}


def test_api_without_key(client, init_db):
    """GET /api/assets ohne X-API-Key-Header: 401 mit JSON-Fehler."""
    response = client.get("/api/assets")

    assert response.status_code == 401
    assert "error" in response.get_json()


def test_api_get_assets(client, test_user, test_asset, api_headers):
    """GET /api/assets mit gültigem Key: 200 und JSON-Liste mit dem Asset."""
    response = client.get("/api/assets", headers=api_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["assets"][0]["asset_tag"] == "AST-0001"


def test_api_get_single_asset(client, test_user, test_asset, api_headers):
    """GET /api/assets/<id>: liefert genau das angeforderte Asset."""
    response = client.get(f"/api/assets/{test_asset.id}", headers=api_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == test_asset.id
    assert data["name"] == "ThinkPad X1"
    assert data["status"] == "active"


def test_api_create_asset(client, test_user, api_headers):
    """POST /api/assets mit JSON: 201 und Asset wird angelegt."""
    response = client.post(
        "/api/assets",
        json={
            "name": "API-Laptop",
            "asset_tag": "AST-0002",
            "status": "active",
            "purchase_cost": 999.5,
        },
        headers=api_headers,
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "API-Laptop"
    assert data["asset_tag"] == "AST-0002"
    assert data["created_by"] == test_user.id


def test_api_get_stats(client, test_user, test_asset, test_category, test_location, api_headers):
    """GET /api/stats: JSON mit Gesamtanzahl, Status-Verteilung und Bestandsgrößen."""
    response = client.get("/api/stats", headers=api_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data["total_assets"] == 1
    assert data["status_counts"]["active"] == 1
    assert data["status_counts"]["retired"] == 0
    assert data["category_count"] == 1
    assert data["location_count"] == 1
    assert data["total_value"] == pytest.approx(1899.99)
