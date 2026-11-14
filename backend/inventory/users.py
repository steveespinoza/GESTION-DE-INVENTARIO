from werkzeug.security import generate_password_hash

from .errors import RequestError


def list_users(connection):
    return connection.execute("""
        SELECT u.id, u.username, u.role,
               ARRAY(SELECT location_id FROM user_locations
                     WHERE user_id = u.id ORDER BY location_id) AS "locationIds"
        FROM users u ORDER BY u.username, u.id
    """).fetchall()


def save_user(connection, actor_id, *, username, role, location_ids, user_id=None, password=None):
    if role not in ("admin", "operator"):
        raise RequestError("Selecciona un rol válido.")
    if role == "admin" and location_ids:
        raise RequestError("Un administrador tiene acceso a todas las ubicaciones.")
    if user_id == actor_id and role != "admin":
        raise RequestError("No puedes quitar el rol de administrador a tu propia cuenta.", 409)

    # Serialize changes to roles, then recheck the actor after acquiring the lock.
    connection.execute("SELECT pg_advisory_xact_lock(327016)")
    actor = connection.execute("SELECT role FROM users WHERE id = %s", (actor_id,)).fetchone()
    if actor is None or actor["role"] != "admin":
        raise RequestError("Esta acción requiere permisos de administrador.", 403)
    locations = connection.execute(
        "SELECT id FROM locations WHERE id = ANY(%s)", (location_ids,)
    ).fetchall()
    if len(locations) != len(location_ids):
        raise RequestError("Una de las ubicaciones seleccionadas no existe.")

    if user_id is None:
        user = connection.execute("""
            INSERT INTO users (username, role, password_hash) VALUES (%s, %s, %s)
            RETURNING id, username, role
        """, (username, role, generate_password_hash(password))).fetchone()
    else:
        user = connection.execute("""
            UPDATE users SET username = %s, role = %s WHERE id = %s
            RETURNING id, username, role
        """, (username, role, user_id)).fetchone()
        if user is None:
            raise RequestError("El usuario seleccionado no existe.", 404)
        connection.execute("DELETE FROM user_locations WHERE user_id = %s", (user_id,))

    if location_ids:
        connection.execute("""
            INSERT INTO user_locations (user_id, location_id)
            SELECT %s, location_id FROM unnest(%s::integer[]) AS location_id
        """, (user["id"], location_ids))
    return {**user, "locationIds": location_ids}
