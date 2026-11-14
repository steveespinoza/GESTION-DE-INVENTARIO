from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

from inventory.errors import RequestError
from inventory.movements import parse_quantity

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


def test_receipt_updates_balance_and_history(app, login):
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


def test_operator_cannot_write_outside_scope_or_open_stock(app, login):
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


def test_failed_stock_write_rolls_back_movement(app, login):
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


def test_concurrent_receipts_keep_both_quantities(app, login):
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


def test_issue_updates_balance_and_history(app, login):
    client = app.test_client()
    login(client)
    assert client.post("/api/inventory/receipts", json=receipt(quantity="10.125")).status_code == 201
    issued = client.post("/api/inventory/issues", json=receipt(quantity="8.125"))
    assert issued.status_code == 201
    assert issued.json["balance"] == "2.000"
    inventory = client.get("/api/inventory/locations/1?kind=issue").json
    [movement] = inventory["movements"]
    assert movement["id"] == issued.json["id"]
    assert movement["kind"] == "issue"
    assert movement["quantity"] == "-8.125"
    assert movement["actor"] == "admin-demo"
    assert client.post("/api/inventory/issues", json=receipt(quantity="2")).json["balance"] == "0.000"


def test_rejected_issues_leave_stock_and_history_intact(app, login):
    client = app.test_client()
    login(client)
    assert client.post("/api/inventory/receipts", json=receipt(quantity="10")).status_code == 201
    assert client.post("/api/inventory/issues", json=receipt(quantity="11")).status_code == 409
    assert client.post("/api/inventory/issues", json=receipt(productId=2, quantity="1")).status_code == 409
    assert client.post("/api/inventory/issues", json=receipt(quantity="-1")).status_code == 400
    assert client.post("/api/inventory/receipts", json=receipt(kind="issue")).status_code == 400
    login(client, "operador-demo")
    assert client.post("/api/inventory/issues", json=receipt(quantity="1")).status_code == 403
    login(client)
    inventory = client.get("/api/inventory/locations/1").json
    assert inventory["balances"][0]["quantity"] == "10.000"
    assert [item["kind"] for item in inventory["movements"]] == ["receipt"]


def test_concurrent_issues_cannot_overdraw_stock(app, login):
    client = app.test_client()
    login(client, "operador-demo")
    assert client.post("/api/inventory/receipts", json=receipt(
        locationId=2, quantity="10"
    )).status_code == 201

    ready = Barrier(2, timeout=5)

    def issue(_):
        worker = app.test_client()
        login(worker, "operador-demo")
        ready.wait()
        return worker.post("/api/inventory/issues", json=receipt(
            locationId=2, quantity="8"
        )).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(issue, range(2))) == [201, 409]
    inventory = client.get("/api/inventory/locations/2").json
    assert inventory["balances"][0]["quantity"] == "2.000"
    assert [item["quantity"] for item in inventory["movements"]] == ["-8.000", "10.000"]


def test_failed_issue_movement_rolls_back_debit(app, login):
    client = app.test_client()
    login(client)
    assert client.post("/api/inventory/receipts", json=receipt(quantity="10")).status_code == 201
    with psycopg.connect(app.config["DATABASE_URL"]) as connection:
        connection.execute("ALTER TABLE movements ADD CHECK (kind <> 'issue')")

    with pytest.raises(psycopg.errors.CheckViolation):
        client.post("/api/inventory/issues", json=receipt(quantity="8"))

    inventory = client.get("/api/inventory/locations/1").json
    assert inventory["balances"][0]["quantity"] == "10.000"
    assert [item["kind"] for item in inventory["movements"]] == ["receipt"]


def transfer(**overrides):
    return receipt(destinationId=2, **overrides)


def test_transfer_is_one_movement_visible_in_both_locations(app, login):
    client = app.test_client()
    login(client)
    assert client.post("/api/inventory/receipts", json=receipt()).status_code == 201
    transferred = client.post("/api/inventory/transfers", json=transfer(quantity="30"))
    assert transferred.status_code == 201
    assert transferred.json["balance"] == "70.000"
    assert client.post("/api/inventory/issues", json=receipt(locationId=2, quantity="10")).status_code == 201

    origin = client.get("/api/inventory/locations/1?kind=transfer").json
    destination = client.get("/api/inventory/locations/2?kind=transfer").json
    assert origin["balances"][0]["quantity"] == "70.000"
    assert destination["balances"][0]["quantity"] == "20.000"
    [debit] = origin["movements"]
    [credit] = destination["movements"]
    assert debit["id"] == credit["id"] == transferred.json["id"]
    assert debit["quantity"] == "-30.000"
    assert credit["quantity"] == "30.000"


def test_rejected_transfer_preserves_both_locations(app, login):
    client = app.test_client()
    login(client)
    assert client.post("/api/inventory/receipts", json=receipt(quantity="10")).status_code == 201
    assert client.post("/api/inventory/transfers", json=transfer(quantity="11")).status_code == 409
    assert client.post("/api/inventory/transfers", json=transfer(locationId=2)).status_code == 400
    login(client, "operador-demo")
    assert client.post("/api/inventory/transfers", json=transfer()).status_code == 403
    assert client.post("/api/inventory/transfers", json=receipt(
        locationId=2, destinationId=1
    )).status_code == 403
    login(client)
    origin = client.get("/api/inventory/locations/1").json
    assert origin["balances"][0]["quantity"] == "10.000"
    assert [movement["kind"] for movement in origin["movements"]] == ["receipt"]
    assert client.get("/api/inventory/locations/2").json == {
        "balances": [], "movements": [], "hasMore": False,
    }


def test_destination_failure_rolls_back_transfer(app, login):
    client = app.test_client()
    login(client)
    assert client.post("/api/inventory/receipts", json=receipt(quantity="10")).status_code == 201
    assert client.post("/api/inventory/receipts", json=receipt(
        locationId=2, quantity="999999999999999.999"
    )).status_code == 201
    assert client.post("/api/inventory/transfers", json=transfer(quantity="1")).status_code == 409
    for location_id, quantity in ((1, "10.000"), (2, "999999999999999.999")):
        data = client.get(f"/api/inventory/locations/{location_id}").json
        assert data["balances"][0]["quantity"] == quantity
        assert [movement["kind"] for movement in data["movements"]] == ["receipt"]


def test_concurrent_transfers_in_opposite_directions(app, login):
    client = app.test_client()
    login(client)
    for location_id in (1, 2):
        assert client.post("/api/inventory/receipts", json=receipt(
            locationId=location_id, quantity="10"
        )).status_code == 201

    ready = Barrier(2, timeout=5)

    def send(pair):
        origin, destination = pair
        worker = app.test_client()
        login(worker)
        ready.wait()
        return worker.post("/api/inventory/transfers", json=receipt(
            locationId=origin, destinationId=destination, quantity="8"
        )).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(send, [(1, 2), (2, 1)])) == [201, 201]
    for location_id in (1, 2):
        data = client.get(f"/api/inventory/locations/{location_id}?kind=transfer").json
        assert data["balances"][0]["quantity"] == "10.000"
        assert sorted(item["quantity"] for item in data["movements"]) == ["-8.000", "8.000"]
