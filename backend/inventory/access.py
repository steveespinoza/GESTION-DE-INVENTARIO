from functools import wraps

from flask import Blueprint, g, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .db import database
from .errors import RequestError

auth = Blueprint("auth", __name__, url_prefix="/api/session")
DUMMY_PASSWORD_HASH = generate_password_hash("unused")


def require_session(view):
    @wraps(view)
    def authenticated(*args, **kwargs):
        actor_id = session.get("user_id")
        if actor_id is None:
            raise RequestError("Inicia sesión para continuar.", 401)
        with database() as connection:
            g.actor = connection.execute(
                "SELECT id, username, role FROM users WHERE id = %s", (actor_id,)
            ).fetchone()
        if g.actor is None:
            session.clear()
            raise RequestError("Inicia sesión para continuar.", 401)
        return view(*args, **kwargs)
    return authenticated


def visible_locations(connection, actor):
    if actor["role"] == "admin":
        return connection.execute("SELECT id, name FROM locations ORDER BY name").fetchall()
    return connection.execute("""
        SELECT l.id, l.name FROM locations l
        JOIN user_locations ul ON ul.location_id = l.id
        WHERE ul.user_id = %s ORDER BY l.name
    """, (actor["id"],)).fetchall()


def require_location(connection, actor, location_id):
    allowed = connection.execute("""
        SELECT EXISTS (
            SELECT 1 FROM locations l WHERE l.id = %s
            AND (%s = 'admin' OR EXISTS (
                SELECT 1 FROM user_locations ul
                WHERE ul.location_id = l.id AND ul.user_id = %s
            ))
        ) AS allowed
    """, (location_id, actor["role"], actor["id"])).fetchone()
    if not allowed["allowed"]:
        raise RequestError("No tienes acceso a esa ubicación.", 403)


@auth.post("")
def login():
    body = request.get_json()
    if not isinstance(body, dict):
        raise RequestError("Ingresa tu usuario y contraseña.")
    username, password = body.get("username"), body.get("password")
    if not (
        isinstance(username, str) and 0 < len(username) <= 80
        and isinstance(password, str) and 0 < len(password) <= 256
    ):
        raise RequestError("Ingresa tu usuario y contraseña.")
    with database() as connection:
        user = connection.execute("""
            SELECT id, username, role, password_hash FROM users WHERE username = %s
        """, (username.strip(),)).fetchone()
    valid = check_password_hash(user["password_hash"] if user else DUMMY_PASSWORD_HASH, password)
    if not valid or not user:
        raise RequestError("Usuario o contraseña incorrectos.", 401)
    session.clear()
    session["user_id"] = user["id"]
    session.permanent = True
    return {"username": user["username"], "role": user["role"]}


@auth.get("")
@require_session
def current_session():
    return {"username": g.actor["username"], "role": g.actor["role"]}


@auth.delete("")
def logout():
    session.clear()
    return "", 204
