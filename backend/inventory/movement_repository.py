def product_exists(connection, product_id):
    return connection.execute(
        "SELECT 1 FROM products WHERE id = %s", (product_id,)
    ).fetchone() is not None


def save_movement(connection, *, actor_id, product_id, kind, variations,
                  movement_date, reference):
    movement = connection.execute("""
        INSERT INTO movements (kind, actor_id, movement_date, reference)
        VALUES (%s, %s, %s, %s) RETURNING id, recorded_at
    """, (kind, actor_id, movement_date, reference)).fetchone()
    with connection.cursor() as cursor:
        cursor.executemany("""
            INSERT INTO movement_details (movement_id, product_id, location_id, quantity)
            VALUES (%s, %s, %s, %s)
        """, [(movement["id"], product_id, location_id, quantity)
              for location_id, quantity in variations])
    return movement


def lock_transfer_stock(connection, product_id, origin_id, destination_id):
    # Take the locks in the same order for transfers in either direction.
    for location_id in sorted((origin_id, destination_id)):
        connection.execute("""
            INSERT INTO stock (product_id, location_id, quantity) VALUES (%s, %s, 0)
            ON CONFLICT (product_id, location_id) DO NOTHING
        """, (product_id, location_id))
        connection.execute("""
            SELECT 1 FROM stock WHERE product_id = %s AND location_id = %s FOR UPDATE
        """, (product_id, location_id))


def increase_stock(connection, product_id, location_id, quantity):
    return connection.execute("""
        INSERT INTO stock (product_id, location_id, quantity) VALUES (%s, %s, %s)
        ON CONFLICT (product_id, location_id)
        DO UPDATE SET quantity = stock.quantity + EXCLUDED.quantity
        RETURNING quantity
    """, (product_id, location_id, quantity)).fetchone()


def decrease_stock(connection, product_id, location_id, quantity):
    return connection.execute("""
        UPDATE stock SET quantity = stock.quantity - %s
        WHERE product_id = %s AND location_id = %s AND stock.quantity >= %s
        RETURNING quantity
    """, (quantity, product_id, location_id, quantity)).fetchone()
