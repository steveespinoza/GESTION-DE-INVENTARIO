import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from inventory import create_app
from inventory.errors import RequestError
from inventory.receipts import parse_quantity

DEMO_PASSWORD = "inventario-prueba-local"


@pytest.fixture
def app():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Configura TEST_DATABASE_URL para ejecutar las pruebas de PostgreSQL.")
    schema_name = f"test_receipts_{uuid4().hex}"
    schema = sql.Identifier(schema_name)
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        try:
            app = create_app({
                "DATABASE_URL": make_conninfo(database_url, options=f"-c search_path={schema_name}"),
                "SECRET_KEY": "test-only",
                "SESSION_COOKIE_SECURE": False,
                "TESTING": True,
            })
            runner = app.test_cli_runner()
            for command in (["migrate"], ["migrate"], ["seed-demo", "--password", DEMO_PASSWORD]):
                result = runner.invoke(args=command)
                assert result.exit_code == 0, result.output or repr(result.exception)
            yield app
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))


def login(client, username="admin-demo"):
    result = client.post("/api/session", json={"username": username, "password": DEMO_PASSWORD})
    assert result.status_code == 200


def receipt(**overrides):
    return {
        "locationId": 1, "productId": 1, "kind": "receipt",
        "quantity": "100", "movementDate": "2026-11-13", "reference": "Recepción de prueba",
        **overrides,
    }


@pytest.mark.parametrize("value", ["0", "-1", "1.0001", "NaN", "Infinity", 2.5])
def test_invalid_quantities(value):
    with pytest.raises(RequestError):
        parse_quantity(value)


def test_receipt_updates_balance_and_history(app):
    client = app.test_client()
    login(client)
    created = client.post("/api/inventory/receipts", json=receipt(kind="opening"))
    assert created.status_code == 201
    assert created.json["balance"] == "100.000"
    assert client.post("/api/inventory/receipts", json=receipt(
        quantity="0.125", movementDate="2026-11-14", reference=""
    )).status_code == 201
    inventory = client.get("/api/inventory/locations/1?kind=opening&to=2026-11-13").json
    assert inventory["balances"][0]["quantity"] == "100.125"
    [movement] = inventory["movements"]
    assert movement["id"] == created.json["id"]
    assert movement["kind"] == "opening"
    assert movement["actor"] == "admin-demo"
    assert movement["movementDate"] == "2026-11-13"
    assert movement["reference"] == "Recepción de prueba"
    assert movement["recordedAt"] == created.json["recordedAt"]
    assert client.get("/api/inventory/locations/2").json["movements"] == []


def test_operator_cannot_write_outside_scope_or_open_stock(app):
    client = app.test_client()
    assert client.post("/api/inventory/receipts", json=receipt()).status_code == 401
    login(client, "operador-demo")
    assert client.get("/api/inventory/options").json["locations"] == [{"id": 2, "name": "Almacén B"}]
    assert client.get("/api/inventory/locations/1").status_code == 403
    assert client.post("/api/inventory/receipts", json=receipt()).status_code == 403
    assert client.post("/api/inventory/receipts", json=receipt(
        locationId=2, kind="opening"
    )).status_code == 403
    assert client.post("/api/inventory/receipts", json=receipt(locationId=2)).status_code == 201
    assert client.delete("/api/session").status_code == 204
    assert client.get("/api/session").status_code == 401
    login(client)
    assert client.get("/api/inventory/locations/1").json["balances"] == []
    assert len(client.get("/api/inventory/locations/2").json["movements"]) == 1


def test_failed_stock_write_rolls_back_movement(app):
    client = app.test_client()
    login(client)
    assert client.post("/api/inventory/receipts", json=receipt(
        quantity="999999999999999.999"
    )).status_code == 201
    assert client.post("/api/inventory/receipts", json=receipt(quantity="0.001")).status_code == 409
    inventory = client.get("/api/inventory/locations/1").json
    assert inventory["balances"][0]["quantity"] == "999999999999999.999"
    assert len(inventory["movements"]) == 1
    with psycopg.connect(app.config["DATABASE_URL"]) as connection:
        assert connection.execute("SELECT count(*) FROM movements").fetchone() == (1,)


def test_concurrent_receipts_keep_both_quantities(app):
    def register(quantity):
        client = app.test_client()
        login(client)
        return client.post("/api/inventory/receipts", json=receipt(quantity=quantity)).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(register, ["5.001", "7.002"])) == [201, 201]
    client = app.test_client()
    login(client)
    inventory = client.get("/api/inventory/locations/1").json
    assert inventory["balances"][0]["quantity"] == "12.003"
    assert len(inventory["movements"]) == 2
