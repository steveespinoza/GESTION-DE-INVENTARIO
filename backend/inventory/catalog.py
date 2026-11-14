from .errors import RequestError


def list_products(connection):
    return connection.execute("""
        SELECT id, sku, name, unit, category FROM products ORDER BY name, id
    """).fetchall()


def create_product(connection, fields):
    return connection.execute("""
        INSERT INTO products (sku, name, unit, category) VALUES (%s, %s, %s, %s)
        RETURNING id, sku, name, unit, category
    """, fields).fetchone()


def update_product(connection, product_id, fields):
    product = connection.execute(
        "SELECT unit FROM products WHERE id = %s FOR UPDATE", (product_id,)
    ).fetchone()
    if product is None:
        raise RequestError("El producto seleccionado no existe.", 404)

    _, _, unit, _ = fields
    if product["unit"] != unit and connection.execute(
        "SELECT 1 FROM stock WHERE product_id = %s LIMIT 1", (product_id,)
    ).fetchone():
        raise RequestError("La unidad de medida no se puede cambiar después del primer movimiento.", 409)

    return connection.execute("""
        UPDATE products SET sku = %s, name = %s, unit = %s, category = %s
        WHERE id = %s RETURNING id, sku, name, unit, category
    """, (*fields, product_id)).fetchone()
