from markupsafe import Markup
from sqlalchemy import func

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.main import bp
from app.main.forms import AssetForm, CategoryForm, LocationForm
from app.models import Asset, AssetStatus, Category, Location

STATUS_META = {
    AssetStatus.ACTIVE: ("Aktiv", "success"),
    AssetStatus.MAINTENANCE: ("In Wartung", "warning"),
    AssetStatus.RETIRED: ("Außer Dienst", "secondary"),
    AssetStatus.LOST: ("Verloren", "danger"),
}


def generate_asset_tag() -> str:
    max_number = 0
    for (tag,) in Asset.query.with_entities(Asset.asset_tag).all():
        suffix = tag.rsplit("-", 1)[-1]
        if suffix.isdigit():
            max_number = max(max_number, int(suffix))
    return f"AST-{max_number + 1:04d}"


def _apply_asset_form(asset: Asset, form: AssetForm) -> None:
    asset.name = form.name.data
    asset.description = form.description.data
    asset.serial_number = form.serial_number.data
    asset.status = AssetStatus(form.status.data)
    asset.purchase_date = form.purchase_date.data
    asset.purchase_cost = form.purchase_cost.data
    asset.category_id = form.category_id.data or None
    asset.location_id = form.location_id.data or None

    if asset.status is AssetStatus.RETIRED:
        # Außer Dienst: Zuordnung wird automatisch gelöst
        asset.assigned_to = None
    else:
        asset.assigned_to = form.assigned_to.data or None


@bp.app_template_filter()
def status_badge(status: AssetStatus) -> Markup:
    label, color = STATUS_META.get(status, ("Unbekannt", "secondary"))
    return Markup(f'<span class="badge bg-{color}">{label}</span>')


@bp.app_template_filter()
def chf(value) -> str:
    if value is None:
        return "–"
    formatted = f"{float(value):,.2f}"
    # US-Format (1,500.50) in CH-Format (1'500.50) umwandeln
    formatted = formatted.replace(",", "'")
    return f"CHF {formatted}"


@bp.route("/")
@login_required
def index():
    counts = dict(
        db.session.query(Asset.status, func.count(Asset.id))
        .group_by(Asset.status)
        .all()
    )
    status_stats = [
        (status, label, color, counts.get(status, 0))
        for status, (label, color) in STATUS_META.items()
    ]

    total_value = (
        db.session.query(func.coalesce(func.sum(Asset.purchase_cost), 0))
        .filter(Asset.status == AssetStatus.ACTIVE)
        .scalar()
    )

    recent_assets = Asset.query.order_by(Asset.created_at.desc()).limit(5).all()

    return render_template(
        "main/dashboard.html",
        status_stats=status_stats,
        total_value=total_value,
        recent_assets=recent_assets,
    )


@bp.route("/assets")
@login_required
def assets():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    category_id = request.args.get("category_id", type=int)
    location_id = request.args.get("location_id", type=int)

    query = Asset.query

    if search:
        pattern = f"%{search}%"
        query = query.filter(db.or_(Asset.name.ilike(pattern), Asset.asset_tag.ilike(pattern)))

    if status:
        try:
            query = query.filter(Asset.status == AssetStatus(status))
        except ValueError:
            pass

    if category_id:
        query = query.filter(Asset.category_id == category_id)
    if location_id:
        query = query.filter(Asset.location_id == location_id)

    asset_list = query.order_by(Asset.asset_tag).all()

    return render_template(
        "main/assets.html",
        assets=asset_list,
        search=search,
        status=status,
        category_id=category_id,
        location_id=location_id,
        categories=Category.query.order_by(Category.name).all(),
        locations=Location.query.order_by(Location.name).all(),
        statuses=[(s.value, label) for s, (label, _) in STATUS_META.items()],
    )


@bp.route("/assets/new", methods=["GET", "POST"])
@login_required
def asset_create():
    form = AssetForm()
    form.populate_choices()

    if form.validate_on_submit():
        asset = Asset(
            name=form.name.data,
            asset_tag=generate_asset_tag(),
            created_by=current_user.id,
        )
        _apply_asset_form(asset, form)
        db.session.add(asset)
        db.session.commit()
        flash(f"Asset {asset.asset_tag} wurde angelegt.", "success")
        return redirect(url_for("main.asset_detail", asset_id=asset.id))

    return render_template("main/asset_form.html", form=form, title="Neues Asset")


@bp.route("/assets/<int:asset_id>")
@login_required
def asset_detail(asset_id: int):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        flash("Asset nicht gefunden.", "danger")
        return redirect(url_for("main.assets"))
    return render_template("main/asset_detail.html", asset=asset)


@bp.route("/assets/<int:asset_id>/edit", methods=["GET", "POST"])
@login_required
def asset_edit(asset_id: int):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        flash("Asset nicht gefunden.", "danger")
        return redirect(url_for("main.assets"))

    form = AssetForm(obj=asset)
    # Der Status liegt in der DB als Enum vor; das SelectField erwartet den
    # String-Wert ("active", ...). Nur beim GET normalisieren – beim POST
    # enthält das Feld bereits den vom Nutzer gewählten Wert.
    if not form.status.raw_data:
        form.status.data = asset.status.value
    form.populate_choices()

    if form.validate_on_submit():
        was_assigned = asset.assigned_to is not None
        _apply_asset_form(asset, form)
        db.session.commit()

        if asset.status is AssetStatus.RETIRED and was_assigned:
            flash(
                f"Asset {asset.asset_tag} wurde aktualisiert. "
                "Die Zuweisung wurde wegen des Status 'Außer Dienst' entfernt.",
                "info",
            )
        else:
            flash(f"Asset {asset.asset_tag} wurde aktualisiert.", "success")
        return redirect(url_for("main.asset_detail", asset_id=asset.id))

    return render_template(
        "main/asset_form.html", form=form, title=f"Asset {asset.asset_tag} bearbeiten"
    )


@bp.route("/assets/<int:asset_id>/delete", methods=["POST"])
@login_required
def asset_delete(asset_id: int):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        flash("Asset nicht gefunden.", "danger")
        return redirect(url_for("main.assets"))

    is_creator = asset.created_by == current_user.id
    confirmed = request.form.get("confirm") == "1"

    if not is_creator and not confirmed:
        flash(
            "Nur der Ersteller kann das Asset ohne Bestätigung löschen. "
            "Bitte bestätige die Löschung.",
            "danger",
        )
        return redirect(url_for("main.asset_detail", asset_id=asset.id))

    tag = asset.asset_tag
    db.session.delete(asset)
    db.session.commit()
    flash(f"Asset {tag} wurde gelöscht.", "info")
    return redirect(url_for("main.assets"))


@bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        if Category.query.filter_by(name=form.name.data).first():
            flash("Kategorie existiert bereits.", "danger")
        else:
            category = Category(name=form.name.data, description=form.description.data)
            db.session.add(category)
            db.session.commit()
            flash(f"Kategorie '{category.name}' wurde angelegt.", "success")
            return redirect(url_for("main.categories"))

    category_list = Category.query.order_by(Category.name).all()
    return render_template("main/categories.html", categories=category_list, form=form)


@bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
def category_delete(category_id: int):
    category = db.session.get(Category, category_id)
    if category is None:
        flash("Kategorie nicht gefunden.", "danger")
        return redirect(url_for("main.categories"))

    if category.assets:
        flash(
            f"Kategorie '{category.name}' kann nicht gelöscht werden, "
            f"da {len(category.assets)} Asset(s) zugewiesen sind.",
            "danger",
        )
    else:
        db.session.delete(category)
        db.session.commit()
        flash(f"Kategorie '{category.name}' wurde gelöscht.", "info")

    return redirect(url_for("main.categories"))


@bp.route("/locations", methods=["GET", "POST"])
@login_required
def locations():
    form = LocationForm()
    if form.validate_on_submit():
        if Location.query.filter_by(name=form.name.data).first():
            flash("Standort existiert bereits.", "danger")
        else:
            location = Location(
                name=form.name.data,
                building=form.building.data,
                room=form.room.data,
            )
            db.session.add(location)
            db.session.commit()
            flash(f"Standort '{location.name}' wurde angelegt.", "success")
            return redirect(url_for("main.locations"))

    location_list = Location.query.order_by(Location.name).all()
    return render_template("main/locations.html", locations=location_list, form=form)


@bp.route("/locations/<int:location_id>/delete", methods=["POST"])
@login_required
def location_delete(location_id: int):
    location = db.session.get(Location, location_id)
    if location is None:
        flash("Standort nicht gefunden.", "danger")
        return redirect(url_for("main.locations"))

    if location.assets:
        flash(
            f"Standort '{location.name}' kann nicht gelöscht werden, "
            f"da {len(location.assets)} Asset(s) zugewiesen sind.",
            "danger",
        )
    else:
        db.session.delete(location)
        db.session.commit()
        flash(f"Standort '{location.name}' wurde gelöscht.", "info")

    return redirect(url_for("main.locations"))
