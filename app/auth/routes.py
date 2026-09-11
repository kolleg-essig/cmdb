"""Routes des Auth-Blueprints: Registrierung, Login, Logout und Profil."""
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Neues Benutzerkonto anlegen (inkl. API-Key-Erzeugung); leitet zum Login weiter."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data or "")  # DataRequired garantiert einen Wert
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()

        flash("Registrierung erfolgreich. Bitte melde dich an.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Benutzeranmeldung mit Benutzername + Passwort."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Benutzername oder Passwort ist falsch.", "danger")
            return render_template("auth/login.html", form=form)

        # remember=True verlängert die Session über einen Cookie
        login_user(user, remember=form.remember_me.data)

        # Falls der Nutzer von einer geschützten Seite hereingefallen ist,
        # dort wieder hinleiten (sonst zur Hauptseite):
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.index"))

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
def logout():
    """Benutzer abmelden und zum Login zurückleiten."""
    logout_user()
    flash("Du wurdest abgemeldet.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profile")
@login_required
def profile():
    """Profilseite mit Benutzername, E-Mail und persönlichem API-Key."""
    return render_template("auth/profile.html", user=current_user)
