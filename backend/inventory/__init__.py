import os
from datetime import timedelta
from pathlib import Path

from flask import Flask
from werkzeug.exceptions import HTTPException

from .access import auth
from .db import register_commands
from .errors import RequestError
from .routes import inventory


def create_app(config=None):
    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    app = Flask(__name__, static_folder=dist, static_url_path="/app")
    app.config.from_mapping(
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") != "0",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_NAME="inventario_session",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=16_384,
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"] or not app.config["DATABASE_URL"]:
        raise RuntimeError("Configura SECRET_KEY y DATABASE_URL antes de iniciar Flask.")

    app.register_blueprint(auth)
    app.register_blueprint(inventory)
    register_commands(app)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.errorhandler(RequestError)
    def request_error(error):
        return {"error": str(error)}, error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {400: "La solicitud contiene datos inválidos.",
                    415: "Envía los datos como JSON.",
                    413: "La solicitud supera el tamaño permitido."}
        return {"error": messages.get(error.code, error.name)}, error.code

    return app
