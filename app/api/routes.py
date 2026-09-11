"""
API-Routes: RESTful JSON-Schnittstelle der CMDB.

Authentifizierung erfolgt ohne Browser über den Header:
    X-API-Key: <32-stelliger Hex-Key des Benutzers>

Beispiel-Requests (curl):

    # Alle Assets auflisten
    curl -H "X-API-Key: abc123..." http://localhost:5000/api/assets

    # Assets filtern (Status, Kategorie, Standort, Suche)
    curl -H "X-API-Key: abc123..." "http://localhost:5000/api/assets?status=active&search=ThinkPad"

    # Einzelnes Asset
    curl -H "X-API-Key: abc123..." http://localhost:5000/api/assets/1

    # Neues Asset anlegen
    curl -X POST -H "X-API-Key: abc123..." -H "Content-Type: application/json" \\
        -d '{"name": "ThinkPad X1", "asset_tag": "AST-0042", "status": "active",
             "purchase_cost": 1899.99, "category_id": 1, "location_id": 1,
             "assigned_to": "m.schmidt"}' \\
        http://localhost:5000/api/assets

    # Asset aktualisieren (nur die angegebenen Felder)
    curl -X PUT -H "X-API-Key: abc123..." -H "Content-Type: application/json" \\
        -d '{"status": "maintenance"}' http://localhost:5000/api/assets/1

    # Asset löschen
    curl -X DELETE -H "X-API-Key: abc123..." http://localhost:5000/api/assets/1

    # Kategorien / Standorte / Statistiken
    curl -H "X-API-Key: abc123..." http://localhost:5000/api/categories
    curl -H "X-API-Key: abc123..." http://localhost:5000/api/categories/1
    curl -H "X-API-Key: abc123..." http://localhost:5000/api/locations
    curl -H "X-API-Key: abc123..." http://localhost:5000/api/locations/1
    curl -H "X-API-Key: abc123..." http://localhost:5000/api/stats
"""
from datetime import date
from functools import wraps

from flask import jsonify, request
from sqlalchemy import func

from app import db
from app.api import bp
from app.main.routes import generate_asset_tag
from app.models import Asset, AssetStatus, Category, Location, User


def api_key_required(f):
    """Decorator: prüft den API-Key aus dem Header 'X-API-Key' (401 bei Fehlschlag)."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"error": "Fehlender Header 'X-API-Key'."}), 401
        user = User.query.filter_by(api_key=api_key).first()
        if user is None:
            return jsonify({"error": "Ungültiger API-Key."}), 401
        request.api_user = user
        return f(*args, **kwargs)

    return wrapper


def _error(message: str, status: int):
    """Erzeugt eine einheitliche JSON-Fehlerantwort im Format {"error": "..."}."""
    return jsonify({"error": message}), status


def _parse_date(value, field: str):
    """Prüft ein Datumsfeld im Format JJJJ-MM-TT und liefert ein date-Objekt."""
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"'{field}' muss das Format JJJJ-MM-TT haben (z. B. 2024-05-01).")


def _parse_cost(value, field: str):
    """Prüft ein Kostenfeld und liefert einen Float."""
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{field}' muss eine Zahl sein.")
    if value < 0:
        raise ValueError(f"'{field}' darf nicht negativ sein.")
    return float(value)


def _resolve_id(model, value, field: str, label: str):
    """Löst eine ID auf und prüft, dass die referenzierte Zeile existiert."""
    if value in (None, ""):
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{field}' muss eine Zahl (ID) sein.")
    if db.session.get(model, value) is None:
        raise ValueError(f"{label} mit ID {value} existiert nicht.")
    return value


def _apply_asset_fields(asset: Asset, data: dict) -> None:
    """Überträgt und validiert JSON-Felder auf ein Asset; retired löst die Zuweisung."""
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("'name' ist erforderlich und darf nicht leer sein.")
        asset.name = name.strip()

    if "asset_tag" in data:
        tag = data["asset_tag"]
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError("'asset_tag' darf nicht leer sein.")
        tag = tag.strip()
        existing = Asset.query.filter_by(asset_tag=tag).first()
        if existing is not None and existing.id != asset.id:
            raise ValueError(f"Der Asset-Tag '{tag}' existiert bereits.")
        asset.asset_tag = tag

    if "description" in data:
        asset.description = data["description"] or None

    if "serial_number" in data:
        asset.serial_number = data["serial_number"] or None

    if "status" in data:
        try:
            asset.status = AssetStatus(data["status"])
        except ValueError:
            valid = ", ".join(s.value for s in AssetStatus)
            raise ValueError(f"'status' ist ungültig. Zulässig sind: {valid}.") from None

    # Optionalfelder: nur anwenden, wenn sie im Body enthalten sind
    # (bei PUT dürfen fehlende Felder bestehende Werte nicht löschen)
    if "purchase_date" in data:
        asset.purchase_date = _parse_date(data["purchase_date"], "purchase_date")
    if "purchase_cost" in data:
        asset.purchase_cost = _parse_cost(data["purchase_cost"], "purchase_cost")
    if "category_id" in data:
        asset.category_id = _resolve_id(Category, data["category_id"], "category_id", "Kategorie")
    if "location_id" in data:
        asset.location_id = _resolve_id(Location, data["location_id"], "location_id", "Standort")

    if "assigned_to" in data:
        username = data["assigned_to"]
        if username in (None, ""):
            asset.assigned_to = None
        else:
            if not isinstance(username, str):
                raise ValueError("'assigned_to' muss der Benutzername (String) sein.")
            user = User.query.filter_by(username=username.strip()).first()
            if user is None:
                raise ValueError(f"Benutzer '{username}' existiert nicht.")
            asset.assigned_to = user.id

    # Geschäftsregel: Außer Dienst -> Zuweisung wird automatisch gelöst
    if asset.status is AssetStatus.RETIRED:
        asset.assigned_to = None


@bp.route("/health")
def health():
    """Einfacher Health-Check (ohne Authentifizierung)."""
    return jsonify({"status": "ok"})


@bp.route("/assets", methods=["GET"])
@api_key_required
def list_assets():
    """Listet alle Assets als JSON (filterbar: status, category_id, location_id, search)."""
    query = Asset.query

    status_filter = request.args.get("status")
    if status_filter:
        try:
            query = query.filter(Asset.status == AssetStatus(status_filter))
        except ValueError:
            valid = ", ".join(s.value for s in AssetStatus)
            return _error(f"'status' ist ungültig. Zulässig sind: {valid}.", 400)

    category_id = request.args.get("category_id", type=int)
    if category_id:
        query = query.filter(Asset.category_id == category_id)

    location_id = request.args.get("location_id", type=int)
    if location_id:
        query = query.filter(Asset.location_id == location_id)

    search = request.args.get("search", "").strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(db.or_(Asset.name.ilike(pattern), Asset.asset_tag.ilike(pattern)))

    assets = query.order_by(Asset.asset_tag).all()
    return jsonify({"count": len(assets), "assets": [a.to_dict() for a in assets]})


@bp.route("/assets", methods=["POST"])
@api_key_required
def create_asset():
    """Legt ein neues Asset an (JSON-Body); asset_tag wird bei Bedarf automatisch vergeben."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Der Request-Body muss ein JSON-Objekt sein.", 400)

    asset = Asset(created_by=request.api_user.id)
    try:
        _apply_asset_fields(asset, data)
    except ValueError as exc:
        return _error(str(exc), 400)

    if not asset.asset_tag:
        asset.asset_tag = generate_asset_tag()

    db.session.add(asset)
    db.session.commit()
    return jsonify(asset.to_dict()), 201


@bp.route("/assets/<int:asset_id>", methods=["GET"])
@api_key_required
def get_asset(asset_id: int):
    """Liefert ein einzelnes Asset mit allen Details als JSON."""
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        return _error("Asset nicht gefunden.", 404)
    return jsonify(asset.to_dict())


@bp.route("/assets/<int:asset_id>", methods=["PUT"])
@api_key_required
def update_asset(asset_id: int):
    """Aktualisiert ein Asset – nur die im JSON-Body angegebenen Felder werden geändert."""
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        return _error("Asset nicht gefunden.", 404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return _error("Der Request-Body muss ein nicht leeres JSON-Objekt sein.", 400)

    try:
        _apply_asset_fields(asset, data)
    except ValueError as exc:
        return _error(str(exc), 400)

    db.session.commit()
    return jsonify(asset.to_dict())


@bp.route("/assets/<int:asset_id>", methods=["DELETE"])
@api_key_required
def delete_asset(asset_id: int):
    """Löscht ein Asset."""
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        return _error("Asset nicht gefunden.", 404)

    tag = asset.asset_tag
    db.session.delete(asset)
    db.session.commit()
    return jsonify({"message": f"Asset {tag} wurde gelöscht."})


@bp.route("/categories", methods=["GET"])
@api_key_required
def list_categories():
    """Listet alle Kategorien mit der Anzahl zugewiesener Assets auf."""
    categories = Category.query.order_by(Category.name).all()
    return jsonify({"count": len(categories), "categories": [c.to_dict() for c in categories]})


@bp.route("/categories/<int:category_id>", methods=["GET"])
@api_key_required
def get_category(category_id: int):
    """Liefert eine einzelne Kategorie inkl. Anzahl zugewiesener Assets."""
    category = db.session.get(Category, category_id)
    if category is None:
        return _error("Kategorie nicht gefunden.", 404)
    return jsonify(category.to_dict())


@bp.route("/locations", methods=["GET"])
@api_key_required
def list_locations():
    """Listet alle Standorte mit der Anzahl zugewiesener Assets auf."""
    locations = Location.query.order_by(Location.name).all()
    return jsonify({"count": len(locations), "locations": [loc.to_dict() for loc in locations]})


@bp.route("/locations/<int:location_id>", methods=["GET"])
@api_key_required
def get_location(location_id: int):
    """Liefert einen einzelnen Standort inkl. Anzahl zugewiesener Assets."""
    location = db.session.get(Location, location_id)
    if location is None:
        return _error("Standort nicht gefunden.", 404)
    return jsonify(location.to_dict())


@bp.route("/stats", methods=["GET"])
@api_key_required
def stats():
    """Liefert Dashboard-Daten: Anzahl pro Status, Gesamtwert, Bestandsgrößen."""
    # Anzahl Assets pro Status (Status ohne Treffer -> 0)
    counts = dict(
        db.session.query(Asset.status, func.count(Asset.id))
        .group_by(Asset.status)
        .all()
    )
    status_counts = {status.value: counts.get(status, 0) for status in AssetStatus}

    # Gesamtwert aller aktiven Assets (COALESCE, damit leerer Bestand 0 ergibt)
    total_value = (
        db.session.query(func.coalesce(func.sum(Asset.purchase_cost), 0))
        .filter(Asset.status == AssetStatus.ACTIVE)
        .scalar()
    )

    return jsonify(
        {
            "total_assets": Asset.query.count(),
            "status_counts": status_counts,
            "total_value": float(total_value),
            "category_count": Category.query.count(),
            "location_count": Location.query.count(),
        }
    )
