from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


def _optional_int(value):
    return int(value) if value else None


class AssetForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Beschreibung")
    serial_number = StringField("Seriennummer", validators=[Optional(), Length(max=100)])
    status = SelectField(
        "Status",
        choices=[
            ("active", "Aktiv"),
            ("maintenance", "In Wartung"),
            ("retired", "Außer Dienst"),
            ("lost", "Verloren"),
        ],
        validators=[DataRequired()],
    )
    purchase_date = DateField("Kaufdatum", validators=[Optional()])
    purchase_cost = DecimalField(
        "Kaufpreis (CHF)",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"step": "0.01", "min": "0"},
    )
    category_id = SelectField("Kategorie", coerce=_optional_int, validators=[Optional()])
    location_id = SelectField("Standort", coerce=_optional_int, validators=[Optional()])
    assigned_to = SelectField("Zugeordnet an", coerce=_optional_int, validators=[Optional()])

    def populate_choices(self) -> None:
        from app.models import Category, Location, User

        self.category_id.choices = [("", "– keine –")] + [
            (c.id, c.name) for c in Category.query.order_by(Category.name).all()
        ]
        self.location_id.choices = [("", "– keiner –")] + [
            (l.id, l.name) for l in Location.query.order_by(Location.name).all()
        ]
        self.assigned_to.choices = [("", "– nicht zugeordnet –")] + [
            (u.id, u.username) for u in User.query.order_by(User.username).all()
        ]


class CategoryForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Beschreibung")


class LocationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    building = StringField("Gebäude", validators=[Optional(), Length(max=100)])
    room = StringField("Raum", validators=[Optional(), Length(max=50)])
