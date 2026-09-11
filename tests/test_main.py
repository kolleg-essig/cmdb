"""Tests für den Main-Blueprint: Dashboard, Asset-Anlage, Kategorien, Asset-Liste."""
from app import db
from app.models import Asset, Category


def _login(client, username="testuser", password="testpass123"):
    """Hilfsfunktion: meldet den Test-User über das Login-Formular an."""
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_dashboard_authenticated(client, test_user):
    """Nach Login ist das Dashboard erreichbar (200)."""
    _login(client)
    response = client.get("/")

    assert response.status_code == 200


def test_create_asset(client, test_user):
    """Asset über das Formular anlegen: Redirect und Asset mit generiertem Tag in der DB."""
    _login(client)
    response = client.post(
        "/assets/new",
        data={
            "name": "Neuer Laptop",
            "description": "Vom Formular erstellt",
            "status": "active",
        },
        follow_redirects=False,
    )

    # Erfolgreiche Anlage leitet zur Detailseite weiter
    assert response.status_code == 302

    asset = db.session.query(Asset).filter_by(name="Neuer Laptop").first()
    assert asset is not None
    # Der Tag wird automatisch als AST-0001 vergeben
    assert asset.asset_tag == "AST-0001"
    assert asset.created_by == test_user.id


def test_delete_category_with_assets(client, test_user, test_asset):
    """Kategorie mit Assets löschen: kein Löschen, Fehlermeldung wird angezeigt."""
    _login(client)
    category = db.session.get(Category, test_asset.category_id)

    response = client.post(
        f"/categories/{category.id}/delete",
        follow_redirects=True,
    )

    # Die Kategorie existiert weiterhin
    assert db.session.get(Category, category.id) is not None
    # Nach dem Redirect ist die Fehlermeldung im Flash enthalten
    assert "kann nicht gelöscht werden" in response.get_data(as_text=True)


def test_asset_list_accessible(client, test_user, test_asset):
    """Nach Login ist die Asset-Liste erreichbar und enthält das Test-Asset."""
    _login(client)
    response = client.get("/assets")

    assert response.status_code == 200
    assert b"AST-0001" in response.data
