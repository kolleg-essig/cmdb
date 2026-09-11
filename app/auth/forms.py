"""Formulare des Auth-Blueprints (Flask-WTF)."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app import db
from app.models import User


def username_is_unique(form, field):
    """Prüft, ob der Benutzername bereits in der Datenbank existiert."""
    if (
        db.session.query(User.id)
        .filter(User.username == field.data)
        .first()
        is not None
    ):
        raise ValidationError("Der Benutzername ist bereits vergeben.")


def email_is_unique(form, field):
    """Prüft, ob die E-Mail-Adresse bereits in der Datenbank existiert."""
    if (
        db.session.query(User.id)
        .filter(User.email == field.data)
        .first()
        is not None
    ):
        raise ValidationError("Die E-Mail-Adresse ist bereits registriert.")


class RegistrationForm(FlaskForm):
    """Registrierungsformular (Eindeutigkeit von Name/E-Mail, min. 8 Zeichen Passwort)."""

    username = StringField(
        "Benutzername",
        validators=[
            DataRequired(message="Bitte gib einen Benutzernamen ein."),
            Length(min=3, max=80, message="Der Benutzername muss 3–80 Zeichen lang sein."),
            username_is_unique,
        ],
    )
    email = StringField(
        "E-Mail",
        validators=[
            DataRequired(message="Bitte gib eine E-Mail-Adresse ein."),
            Email(message="Bitte gib eine gültige E-Mail-Adresse ein."),
            Length(max=120),
            email_is_unique,
        ],
    )
    password = PasswordField(
        "Passwort",
        validators=[
            DataRequired(message="Bitte gib ein Passwort ein."),
            Length(min=8, max=128, message="Das Passwort muss mindestens 8 Zeichen lang sein."),
        ],
    )
    password_confirm = PasswordField(
        "Passwort bestätigen",
        validators=[
            DataRequired(message="Bitte bestätige das Passwort."),
            EqualTo("password", message="Die Passwörter stimmen nicht überein."),
        ],
    )
    submit = BooleanField("Registrieren")  # Platzhalter; Submit über Button-Element


class LoginForm(FlaskForm):
    """Login-Formular mit Option, die Session zu merken."""

    username = StringField("Benutzername", validators=[DataRequired()])
    password = PasswordField("Passwort", validators=[DataRequired()])
    remember_me = BooleanField("Angemeldet bleiben")
