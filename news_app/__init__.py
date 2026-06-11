import os
from pathlib import Path

from flask import Flask

from news_app.extensions import create_schema, init_database, login_manager, remove_session
from news_app.models import User
from news_app.routes import bp
from news_app.scheduler import start_scheduler


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        DATABASE_URL=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + str(Path(app.instance_path) / "news_aggregator.sqlite"),
        ),
        DISABLE_SCHEDULER=os.environ.get("NEWS_AGGREGATOR_DISABLE_SCHEDULER", "0") == "1",
        REFRESH_INTERVAL_MINUTES=int(os.environ.get("REFRESH_INTERVAL_MINUTES", "15")),
    )
    if config:
        app.config.update(config)

    init_database(app.config["DATABASE_URL"])
    create_schema()

    login_manager.init_app(app)
    login_manager.login_view = "main.login"
    app.register_blueprint(bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    @app.teardown_appcontext
    def shutdown_session(_exception=None):
        remove_session()

    @app.cli.command("init-db")
    def init_db_command():
        create_schema()
        print("Database initialized.")

    if not app.config["DISABLE_SCHEDULER"]:
        start_scheduler(app)

    return app
