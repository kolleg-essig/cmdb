from typing import Optional

from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_object: Optional[str] = None) -> Flask:
    from app import config as config_module

    if config_object is None:
        config_object = config_module.config.get(
            config_module.Config.FLASK_ENV,
            config_module.config["default"],
        )

    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Bitte melde dich an, um diese Seite zu sehen."
    login_manager.login_message_category = "warning"

    from app.api import bp as api_bp
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models import User

        return db.session.get(User, int(user_id))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return render_template("errors/500.html"), 500

    return app
