"""Tests für den Auth-Blueprint: Registrierung, Login und geschützte Routen."""
from app import db
from app.models import User


def test_register_valid(client, init_db):
    """Gültige Registrierung: Redirect zum Login und User existiert in der DB."""
    response = client.post(
        "/auth/register",
        data={
            "username": "neueruser",
            "email": "neu@beispiel.ch",
            "password": "geheim123",
            "password_confirm": "geheim123",
        },
        follow_redirects=False,
    )

    # Erfolgreiche Registrierung leitet zur Login-Seite weiter
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]

    user = db.session.query(User).filter_by(username="neueruser").first()
    assert user is not None
    assert user.check_password("geheim123")
    assert user.api_key is not None


def test_register_duplicate_username(client, test_user):
    """Doppelter Benutzername: Validierung schlägt fehl, es entsteht kein zweiter User."""
    response = client.post(
        "/auth/register",
        data={
            "username": "testuser",  # existiert bereits (Fixture)
            "email": "anders@test.ch",
            "password": "geheim123",
            "password_confirm": "geheim123",
        },
        follow_redirects=False,
    )

    # Formular wird ohne Redirect neu gerendert
    assert response.status_code == 200
    assert db.session.query(User).count() == 1


def test_login_valid(client, test_user):
    """Gültiger Login: Redirect (302) zur Hauptseite."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_login_invalid(client, test_user):
    """Falsches Passwort: kein Redirect, Fehlermeldung wird angezeigt."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "falsches-passwort"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Benutzername oder Passwort ist falsch." in response.data


def test_protected_route_without_login(client, init_db):
    """Dashboard ohne Login: Redirect zur Login-Seite."""
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
