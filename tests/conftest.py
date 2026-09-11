"""Zentrale Test-Konfiguration und gemeinsame Fixtures für alle Testdateien."""
import pytest

from app import create_app, db
from app.models import Asset, AssetStatus, Category, Location, User


class TestConfig:
    """Test-Konfiguration: SQLite in-memory, CSRF deaktiviert."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-schluessel"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture
def app():
    """Flask-App mit der Test-Konfiguration."""
    app = create_app(TestConfig)
    yield app


@pytest.fixture
def init_db(app):
    """Erstellt alle Tabellen, räumt nach jedem Test wieder auf."""
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    yield
    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture
def client(app, init_db):
    """Flask-Test-Client (nutzt implizit init_db für den App-Kontext)."""
    return app.test_client()


@pytest.fixture
def test_user(init_db):
    """Legt einen Test-Benutzer mit API-Key an und gibt ihn zurück."""
    user = User(username="testuser", email="test@test.ch")
    user.set_password("testpass123")
    user.generate_api_key()
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_category(init_db):
    """Legt eine Test-Kategorie an."""
    category = Category(name="Laptops", description="Mobilrechner")
    db.session.add(category)
    db.session.commit()
    return category


@pytest.fixture
def test_location(init_db):
    """Legt einen Test-Standort an."""
    location = Location(name="Hauptsitz", building="Haus A", room="201")
    db.session.add(location)
    db.session.commit()
    return location


@pytest.fixture
def test_asset(test_user, test_category, test_location):
    """Legt ein Asset mit Kategorie, Standort und Zuweisung an."""
    asset = Asset(
        name="ThinkPad X1",
        asset_tag="AST-0001",
        description="Test-Asset",
        status=AssetStatus.ACTIVE,
        purchase_cost=1899.99,
        category_id=test_category.id,
        location_id=test_location.id,
        assigned_to=test_user.id,
        created_by=test_user.id,
    )
    db.session.add(asset)
    db.session.commit()
    return asset
