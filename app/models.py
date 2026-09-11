import secrets
from datetime import datetime
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class AssetStatus(Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    LOST = "lost"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(32), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    assets = db.relationship(
        "Asset",
        foreign_keys="Asset.assigned_to",
        back_populates="assignee",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self) -> str:
        self.api_key = secrets.token_hex(16)  # 16 Byte = 32 Hex-Zeichen
        return self.api_key

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    assets = db.relationship("Asset", back_populates="category")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "asset_count": len(self.assets),
        }

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Location(db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    building = db.Column(db.String(100), nullable=True)
    room = db.Column(db.String(50), nullable=True)

    assets = db.relationship("Asset", back_populates="location")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "building": self.building,
            "room": self.room,
            "asset_count": len(self.assets),
        }

    def __repr__(self) -> str:
        return f"<Location {self.name}>"


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    serial_number = db.Column(db.String(100), nullable=True)
    status = db.Column(
        db.Enum(AssetStatus, native_enum=False, length=20),
        default=AssetStatus.ACTIVE,
        nullable=False,
    )
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Numeric(12, 2), nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)

    # Zuordnung: wer ist verantwortlich / wer hat das Asset angelegt
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    category = db.relationship("Category", back_populates="assets")
    location = db.relationship("Location", back_populates="assets")
    assignee = db.relationship("User", foreign_keys=[assigned_to], back_populates="assets")
    creator = db.relationship("User", foreign_keys=[created_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "asset_tag": self.asset_tag,
            "description": self.description,
            "serial_number": self.serial_number,
            "status": self.status.value if self.status else None,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "purchase_cost": float(self.purchase_cost) if self.purchase_cost is not None else None,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "location_id": self.location_id,
            "location_name": self.location.name if self.location else None,
            "assigned_to": self.assigned_to,
            "assigned_to_username": self.assignee.username if self.assignee else None,
            "created_by": self.created_by,
            "created_by_username": self.creator.username if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Asset {self.asset_tag}: {self.name}>"
