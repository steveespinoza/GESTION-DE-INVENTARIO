from flask import Blueprint, g, request
from psycopg.errors import UniqueViolation

from .access import require_admin, visible_locations
from .catalog import create_product, list_products, update_product
from .db import database
from .errors import RequestError
from .users import list_users, save_user
from .validation import parse_id

administration = Blueprint("administration", __name__, url_prefix="/api/admin")


def read_fields(*specifications):
    body = request.get_json()
    if not isinstance(body, dict):
        raise RequestError("Envía los datos del formulario.")

    fields = []
    for key, label, limit in specifications:
        value = body.get(key)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit or "\0" in value:
            raise RequestError(f"{label} debe tener entre 1 y {limit} caracteres.")
        fields.append(value.strip())
    return tuple(fields)


def product_fields():
    return read_fields(
        ("sku", "El SKU", 60), ("name", "El nombre", 120),
        ("unit", "La unidad de medida", 30), ("category", "La categoría", 80),
    )


@administration.get("/products")
@require_admin
def products():
    with database() as connection:
        return {"products": list_products(connection)}


@administration.post("/products")
@require_admin
def add_product():
    fields = product_fields()
    try:
        with database() as connection:
            return create_product(connection, fields), 201
    except UniqueViolation:
        raise RequestError("Ya existe un producto con ese SKU.", 409) from None


@administration.put("/products/<int:product_id>")
@require_admin
def edit_product(product_id):
    parse_id(product_id)
    fields = product_fields()
    try:
        with database() as connection:
            return update_product(connection, product_id, fields)
    except UniqueViolation:
        raise RequestError("Ya existe un producto con ese SKU.", 409) from None


@administration.get("/locations")
@require_admin
def locations():
    with database() as connection:
        return {"locations": visible_locations(connection, g.actor)}


@administration.post("/locations")
@require_admin
def add_location():
    fields = read_fields(("name", "El nombre de la ubicación", 120))
    try:
        with database() as connection:
            location = connection.execute(
                "INSERT INTO locations (name) VALUES (%s) RETURNING id, name", fields
            ).fetchone()
        return location, 201
    except UniqueViolation:
        raise RequestError("Ya existe una ubicación con ese nombre.", 409) from None


@administration.put("/locations/<int:location_id>")
@require_admin
def edit_location(location_id):
    parse_id(location_id)
    (name,) = read_fields(("name", "El nombre de la ubicación", 120))
    try:
        with database() as connection:
            location = connection.execute("""
                UPDATE locations SET name = %s WHERE id = %s RETURNING id, name
            """, (name, location_id)).fetchone()
            if location is None:
                raise RequestError("La ubicación seleccionada no existe.", 404)
        return location
    except UniqueViolation:
        raise RequestError("Ya existe una ubicación con ese nombre.", 409) from None


@administration.get("/users")
@require_admin
def users():
    with database() as connection:
        return {
            "users": list_users(connection),
            "locations": visible_locations(connection, g.actor),
        }


@administration.post("/users")
@require_admin
def add_user():
    return write_user(), 201


@administration.put("/users/<int:user_id>")
@require_admin
def edit_user(user_id):
    return write_user(parse_id(user_id))


def write_user(user_id=None):
    (username,) = read_fields(("username", "El usuario", 80))
    body = request.get_json()
    locations = body.get("locationIds")
    if not isinstance(locations, list):
        raise RequestError("Selecciona las ubicaciones del usuario.")
    location_ids = sorted({parse_id(location_id) for location_id in locations})

    password = body.get("password")
    if user_id is None and not (
        isinstance(password, str) and 12 <= len(password) <= 256 and password.strip()
    ):
        raise RequestError("La contraseña debe tener entre 12 y 256 caracteres.")

    try:
        with database() as connection:
            return save_user(
                connection, g.actor["id"], username=username, role=body.get("role"),
                location_ids=location_ids, user_id=user_id, password=password,
            )
    except UniqueViolation:
        raise RequestError("Ya existe una cuenta con ese usuario.", 409) from None
