"""API-Blueprint: JSON-Schnittstelle mit API-Key-Authentifizierung."""
from flask import Blueprint

from app import csrf

bp = Blueprint("api", __name__)

csrf.exempt(bp)

from app.api import routes
