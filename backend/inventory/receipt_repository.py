def product_exists(connection, product_id):
    return connection.execute(
        "SELECT 1 FROM products WHERE id = %s", (product_id,)
    ).fetchone() is not None


def save_receipt(connection, *, actor_id, product_id, location_id, kind, quantity,
                 movement_date, reference):
    movement = connection.execute("""
        INSERT INTO movements (kind, actor_id, movement_date, reference)
        VALUES (%s, %s, %s, %s) RETURNING id, recorded_at
    """, (kind, actor_id, movement_date, reference)).fetchone()
    connection.execute("""
        INSERT INTO movement_details (movement_id, product_id, location_id, quantity)
        VALUES (%s, %s, %s, %s)
    """, (movement["id"], product_id, location_id, quantity))
    stock = connection.execute("""
        INSERT INTO stock (product_id, location_id, quantity) VALUES (%s, %s, %s)
        ON CONFLICT (product_id, location_id)
        DO UPDATE SET quantity = stock.quantity + EXCLUDED.quantity
        RETURNING quantity
    """, (product_id, location_id, quantity)).fetchone()
    return {
        "id": movement["id"],
        "recordedAt": movement["recorded_at"].isoformat(),
        "balance": str(stock["quantity"]),
    }
