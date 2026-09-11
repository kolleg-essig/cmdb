"""
Seed-Script: belegt die Datenbank mit Beispieldaten.

Anwendung:
    python seed.py

Das Script ist idempotent – es kann beliebig oft ausgeführt werden,
ohne dass Duplikate entstehen. Vorhandene Datensätze werden erkannt
und übersprungen (der Admin-User wird bei Bedarf aktualisiert).

Beispieldaten:
    - 1 Admin-User (admin / admin123) mit bekanntem API-Key
    - 5 Kategorien
    - 4 Standorte
    - 12 Assets mit unterschiedlichem Status, Kategorie und Standort
"""
from datetime import date

from app import create_app, db
from app.models import Asset, AssetStatus, Category, Location, User

# Bekannter API-Key des Admins – 32-stelliger Hex-String (für API-Tests)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_EMAIL = "admin@example.com"
ADMIN_API_KEY = "a1b2c3d4e5f60718293a4b5c6d7e8f90"

# (Name, Beschreibung)
CATEGORIES = [
    ("Laptop", "Tragbare Rechner für mobile Mitarbeiter"),
    ("Desktop", "Stationäre Arbeitsplätze"),
    ("Server", "Server im Rechenzentrum bzw. Serverraum"),
    ("Monitor", "Displays und Monitore"),
    ("Netzwerkgerät", "Router, Switches, Access Points und Firewall"),
]

# (Name, Gebäude, Raum)
LOCATIONS = [
    ("Büro Zürich", "Gebäude A", "Raum 101"),
    ("Büro Bern", "Gebäude B", "Raum 204"),
    ("Serverraum Zürich", "Gebäude A", "Raum 002"),
    ("Homeoffice", None, None),
]

# (Tag, Name, Serial, Status, Kategorie, Standort, Kaufdatum, Kosten, Beschreibung)
ASSETS = [
    ("AST-0001", "ThinkPad X1 Carbon", "PF-2024-1101", "active", "Laptop", "Büro Zürich", date(2024, 3, 15), 1899.00, "Arbeitsplatz CTO"),
    ("AST-0002", "MacBook Pro 14", "PF-2024-1102", "active", "Laptop", "Büro Bern", date(2024, 3, 15), 2499.00, "Arbeitsplatz Entwicklung"),
    ("AST-0003", "ThinkPad T14", "PF-2023-0871", "maintenance", "Laptop", "Homeoffice", date(2023, 6, 1), 1299.00, "Akku defekt, in Reparatur"),
    ("AST-0004", "HP ProDesk 400 G9", "PF-2022-0311", "active", "Desktop", "Büro Zürich", date(2022, 9, 20), 899.00, None),
    ("AST-0005", "Dell OptiPlex 7010", "PF-2021-0142", "retired", "Desktop", "Büro Bern", date(2021, 2, 10), 749.00, "Auskunft: Altbestand 2021"),
    ("AST-0006", "Mac Studio M2", "PF-2024-1103", "active", "Desktop", "Büro Zürich", date(2024, 5, 2), 2299.00, "Build-Station"),
    ("AST-0007", "Dell PowerEdge R750", "PF-2023-0455", "active", "Server", "Serverraum Zürich", date(2023, 4, 18), 8450.00, "Produktionsserver (VM-Host 1)"),
    ("AST-0008", "HPE ProLiant DL380", "PF-2021-0098", "maintenance", "Server", "Serverraum Zürich", date(2021, 11, 5), 9200.00, "Festplatten-Wechsel ausstehend"),
    ("AST-0009", "Dell UltraSharp 27", "PF-2024-1104", "active", "Monitor", "Büro Zürich", date(2024, 3, 15), 449.00, None),
    ("AST-0010", "LG UltraFine 24", "PF-2023-0622", "lost", "Monitor", "Büro Bern", date(2023, 7, 30), 399.00, "Verschollen – Suche läuft"),
    ("AST-0011", "Cisco Catalyst 9200", "PF-2022-0733", "active", "Netzwerkgerät", "Serverraum Zürich", date(2022, 10, 12), 3150.00, "L3-Switch Stockwerk 1"),
    ("AST-0012", "Ubiquiti UniFi AP", "PF-2024-1105", "active", "Netzwerkgerät", "Homeoffice", date(2024, 6, 1), 189.00, "WLAN-Zugangspunkt Homeoffice"),
]


def seed_admin() -> User:
    """Legt den Admin-User an bzw. aktualisiert ihn (idempotent)."""
    user = User.query.filter_by(username=ADMIN_USERNAME).first()
    if user is None:
        user = User(username=ADMIN_USERNAME, email=ADMIN_EMAIL)
        user.set_password(ADMIN_PASSWORD)
        user.api_key = ADMIN_API_KEY
        db.session.add(user)
        print(f"  + Admin-User '{ADMIN_USERNAME}' angelegt (API-Key: {ADMIN_API_KEY})")
    else:
        # Bestehenden Admin auf bekannte Werte bringen (Passwort + API-Key)
        user.set_password(ADMIN_PASSWORD)
        user.email = ADMIN_EMAIL
        user.api_key = ADMIN_API_KEY
        print(f"  = Admin-User '{ADMIN_USERNAME}' bereits vorhanden – aktualisiert")
    return user


def seed_categories() -> dict:
    """Legt die Kategorien an und liefert sie als Name->Objekt-Dictionary."""
    result = {}
    for name, description in CATEGORIES:
        category = Category.query.filter_by(name=name).first()
        if category is None:
            category = Category(name=name, description=description)
            db.session.add(category)
            print(f"  + Kategorie '{name}' angelegt")
        else:
            print(f"  = Kategorie '{name}' bereits vorhanden")
        result[name] = category
    db.session.flush()  # IDs für die Asset-Zuordnung verfügbar machen
    return result


def seed_locations() -> dict:
    """Legt die Standorte an und liefert sie als Name->Objekt-Dictionary."""
    result = {}
    for name, building, room in LOCATIONS:
        location = Location.query.filter_by(name=name).first()
        if location is None:
            location = Location(name=name, building=building, room=room)
            db.session.add(location)
            print(f"  + Standort '{name}' angelegt")
        else:
            print(f"  = Standort '{name}' bereits vorhanden")
        result[name] = location
    db.session.flush()
    return result


def seed_assets(admin: User, categories: dict, locations: dict) -> None:
    """Legt die Beispiel-Assets an (Übersprung, falls der Tag schon existiert)."""
    for tag, name, serial, status, cat, loc, purchase_date, cost, description in ASSETS:
        if Asset.query.filter_by(asset_tag=tag).first() is not None:
            print(f"  = Asset '{tag}' bereits vorhanden")
            continue
        asset = Asset(
            name=name,
            asset_tag=tag,
            serial_number=serial,
            status=AssetStatus(status),
            description=description,
            purchase_date=purchase_date,
            purchase_cost=cost,
            category=categories[cat],
            location=locations[loc],
            assigned_to=admin.id,
            created_by=admin.id,
        )
        db.session.add(asset)
        print(f"  + Asset '{tag}' ({name}) angelegt")


def main() -> None:
    app = create_app()
    with app.app_context():
        print("Seed-Script startet ...")
        admin = seed_admin()
        categories = seed_categories()
        locations = seed_locations()
        seed_assets(admin, categories, locations)
        db.session.commit()
        print(
            "Fertig. Login: admin / admin123 | "
            f"API-Key: {ADMIN_API_KEY}"
        )


if __name__ == "__main__":
    main()
