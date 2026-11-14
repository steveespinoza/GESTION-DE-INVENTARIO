def test_administrator_creates_inventory_and_edits_metadata(app, login):
    client = app.test_client()
    login(client)
    fields = {"sku": " TUB-01 ", "name": "Tubo", "unit": "m", "category": "Materiales"}
    product = client.post("/api/admin/products", json=fields)
    location = client.post("/api/admin/locations", json={"name": "Almacén C"})
    assert product.status_code == location.status_code == 201
    assert product.json["sku"] == "TUB-01"
    product_id = product.json["id"]
    location_id = location.json["id"]
    product_url = f"/api/admin/products/{product_id}"
    location_url = f"/api/admin/locations/{location_id}"
    assert client.put(product_url, json={**fields, "unit": "kg"}).status_code == 200
    assert client.post("/api/inventory/receipts", json={
        "productId": product_id, "locationId": location_id, "kind": "receipt",
        "quantity": "12", "movementDate": "2026-11-13",
    }).status_code == 201

    assert client.put(product_url, json=fields).status_code == 409
    updated = client.put(product_url, json={**fields, "name": "Tubo de acero", "unit": "kg"})
    renamed = client.put(location_url, json={"name": "Almacén de metales"})
    assert updated.status_code == renamed.status_code == 200
    assert updated.json["id"] == product_id
    assert renamed.json["id"] == location_id
    assert updated.json in client.get("/api/admin/products").json["products"]
    assert renamed.json in client.get("/api/admin/locations").json["locations"]
    inventory = client.get(f"/api/inventory/locations/{location_id}").json
    assert inventory["balances"][0]["quantity"] == "12.000"
    [movement] = inventory["movements"]
    assert (movement["product"], movement["unit"], movement["quantity"]) == (
        "Tubo de acero", "kg", "12.000",
    )


def test_invalid_and_duplicate_catalog_values_are_rejected(app, login):
    client = app.test_client()
    login(client)
    fields = {"sku": "MAT-001", "name": "Tubo", "unit": "m", "category": "Materiales"}
    assert client.post("/api/admin/products", json=fields).status_code == 409
    assert client.put("/api/admin/products/2", json=fields).status_code == 409
    assert client.post("/api/admin/products", json={**fields, "name": " "}).status_code == 400
    assert client.put("/api/admin/products/123", json=fields).status_code == 404
    assert client.post("/api/admin/locations", json={"name": " Almacén A "}).status_code == 409
    assert client.put("/api/admin/locations/2", json={"name": "Almacén A"}).status_code == 409
    assert client.post("/api/admin/locations", json={"name": " "}).status_code == 400
    assert client.put("/api/admin/locations/123", json={"name": "Central"}).status_code == 404


def test_operator_uses_inventory_catalog_without_administration_access(app, login):
    client = app.test_client()
    assert client.get("/api/admin/products").status_code == 401
    login(client, "operador-demo")
    for resource in ("products", "locations"):
        url = f"/api/admin/{resource}"
        assert client.get(url).status_code == 403
        assert client.post(url, json={}).status_code == 403
        assert client.put(f"{url}/1", json={}).status_code == 403
    options = client.get("/api/inventory/options").json
    assert options["locations"] == [{"id": 2, "name": "Almacén B"}]
    assert {item["sku"] for item in options["products"]} == {"MAT-001", "MAT-002"}
