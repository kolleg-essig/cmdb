# IT-Asset-Inventar (Mini-CMDB)

Webanwendung zur Erfassung und Verwaltung von IT-Assets (Laptops, Server, Netzwerkgeräte u. a.) mit Dashboard, Web-UI, Benutzerkonten und REST-API.

## Technologie-Stack

| Bereich         | Technologie                              |
|-----------------|------------------------------------------|
| Sprache         | Python 3.10+                             |
| Web-Framework   | Flask 3                                  |
| Datenbank       | PostgreSQL                               |
| ORM             | SQLAlchemy 2 + Flask-SQLAlchemy          |
| Migrations      | Flask-Migrate (Alembic)                  |
| Auth            | Flask-Login (Web), API-Key-Header (API)  |
| Formulare       | Flask-WTF (inkl. CSRF-Schutz)            |
| Frontend        | Bootstrap 5 (CDN) + eigenes CSS          |
| Server (Prod.)  | Gunicorn                                 |

## Installation & Setup

```bash
# 1. Projekt klonen und in das Verzeichnis wechseln
cd CMDB

# 2. Virtuelle Umgebung anlegen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Umgebungsvariablen anlegen
cp .env.example .env
#    .env anpassen: DATABASE_URL (PostgreSQL-Zugangsdaten) und SECRET_KEY
#    (SECRET_KEY z. B. generieren: python -c "import secrets; print(secrets.token_hex(32))")

# 5. Datenbank anlegen
createdb asset_manager
#    bzw. psql: CREATE DATABASE asset_manager;

# 6. Datenbank-Migrationen ausführen
flask --app app db upgrade

# 7. Beispieldaten einfügen (idempotent – kann mehrfach ausgeführt werden)
python seed.py
```

## Starten

### Development

```bash
python run.py
# → http://localhost:5000
```

### Production (Gunicorn)

```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
# → http://localhost:80
```

Die Konfiguration (`workers`, `bind`, `timeout` u. a.) liegt in `gunicorn.conf.py`.
Für den Produktivbetrieb `FLASK_ENV=production` in der `.env` setzen.

## Beispieldaten (nach `python seed.py`)

| Konto   | Benutzername | Passwort  |
|---------|--------------|-----------|
| Admin   | `admin`      | `admin123`|

**API-Key des Admins:** `a1b2c3d4e5f60718293a4b5c6d7e8f90`

Weitere Konten können über `/auth/register` angelegt werden; der persönliche
API-Key ist nach dem Login unter **Profil** einsehbar.

## API-Dokumentation

Basis-URL: `http://localhost:5000/api` (Development) bzw. `http://localhost:80/api` (Production).

Authentifizierung über den Header `X-API-Key` (außer `/api/health`).
Fehler werden einheitlich als `{"error": "..."}` mit passendem HTTP-Status (400/401/404) zurückgegeben.

### Endpunkte

| Methode | URL                   | Beschreibung                                              |
|---------|-----------------------|-----------------------------------------------------------|
| GET     | `/api/health`         | Health-Check (ohne Auth)                                  |
| GET     | `/api/assets`         | Assets auflisten, filterbar: `status`, `category_id`, `location_id`, `search` |
| POST    | `/api/assets`         | Neues Asset anlegen (`asset_tag` optional – wird sonst automatisch vergeben) |
| GET     | `/api/assets/<id>`    | Einzelnes Asset abrufen                                   |
| PUT     | `/api/assets/<id>`    | Asset aktualisieren (nur übergebene Felder)               |
| DELETE  | `/api/assets/<id>`    | Asset löschen                                             |
| GET     | `/api/categories`     | Alle Kategorien mit Asset-Anzahl                          |
| GET     | `/api/categories/<id>`| Einzelne Kategorie                                        |
| GET     | `/api/locations`      | Alle Standorte mit Asset-Anzahl                           |
| GET     | `/api/locations/<id>` | Einzelner Standort                                        |
| GET     | `/api/stats`          | Dashboard-Statistiken (Anzahl pro Status, Gesamtwert)     |

Zulässige Status-Werte: `active`, `maintenance`, `retired`, `lost`.
**Geschäftsregel:** Wird ein Asset auf `retired` gesetzt, wird die Zuweisung (`assigned_to`) automatisch gelöst.

### Beispiele

```bash
KEY="a1b2c3d4e5f60718293a4b5c6d7e8f90"
BASE="http://localhost:5000/api"

# Health-Check (ohne Auth)
curl $BASE/health

# Alle Assets auflisten
curl -H "X-API-Key: $KEY" $BASE/assets

# Assets filtern: aktive Laptops (Kategorie 1) mit Suchbegriff
curl -H "X-API-Key: $KEY" "$BASE/assets?status=active&category_id=1&search=ThinkPad"

# Einzelnes Asset
curl -H "X-API-Key: $KEY" $BASE/assets/1

# Neues Asset anlegen
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"name": "ThinkPad X1", "asset_tag": "AST-0100", "status": "active",
       "purchase_date": "2025-01-15", "purchase_cost": 1899.99,
       "category_id": 1, "location_id": 1, "assigned_to": "admin"}' \
  $BASE/assets

# Asset aktualisieren (nur Status ändern)
curl -X PUT -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"status": "maintenance"}' $BASE/assets/1

# Asset löschen
curl -X DELETE -H "X-API-Key: $KEY" $BASE/assets/1

# Kategorien / Standorte / Statistiken
curl -H "X-API-Key: $KEY" $BASE/categories
curl -H "X-API-Key: $KEY" $BASE/categories/1
curl -H "X-API-Key: $KEY" $BASE/locations
curl -H "X-API-Key: $KEY" $BASE/locations/1
curl -H "X-API-Key: $KEY" $BASE/stats
```
