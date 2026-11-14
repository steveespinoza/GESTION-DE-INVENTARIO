OPERATOR = {
    "username": "operador-turno",
    "password": "prueba-turno-2026",
    "role": "operator",
    "locationIds": [1],
}


def test_assignment_changes_apply_to_an_open_session(app, login):
    admin = app.test_client()
    operator = app.test_client()
    login(admin)
    created = admin.post("/api/admin/users", json=OPERATOR)
    assert created.status_code == 201
    user = created.json
    assert set(user) == {"id", "username", "role", "locationIds"}
    assert user in admin.get("/api/admin/users").json["users"]
    assert operator.post("/api/session", json={
        "username": OPERATOR["username"], "password": OPERATOR["password"],
    }).status_code == 200
    assert operator.get("/api/inventory/options").json["locations"] == [
        {"id": 1, "name": "Almacén A"},
    ]
    entry = {"productId": 1, "locationId": 1, "quantity": "4", "kind": "receipt",
             "movementDate": "2026-11-13"}
    assert operator.post("/api/inventory/receipts", json=entry).status_code == 201
    assert operator.get("/api/inventory/locations/2").status_code == 403

    updated = admin.put(f"/api/admin/users/{user['id']}", json={
        "username": "operador-b", "role": "operator", "locationIds": [2],
    })
    assert updated.status_code == 200
    assert updated.json["locationIds"] == [2]
    assert operator.get("/api/session").json["username"] == "operador-b"
    assert operator.get("/api/inventory/locations/1").status_code == 403
    assert operator.post("/api/inventory/receipts", json=entry).status_code == 403
    assert operator.post("/api/inventory/receipts", json={**entry, "locationId": 2}).status_code == 201
    assert admin.get("/api/inventory/locations/1").json["balances"][0]["quantity"] == "4.000"
    assert admin.get("/api/inventory/locations/2").json["balances"][0]["quantity"] == "4.000"


def test_invalid_user_updates_preserve_access(app, login):
    admin = app.test_client()
    login(admin)
    url = "/api/admin/users"
    created = admin.post(url, json=OPERATOR)
    assert created.status_code == 201
    user_url = f"{url}/{created.json['id']}"
    assert admin.post(url, json=OPERATOR).status_code == 409
    assert admin.post(url, json={**OPERATOR, "password": "short"}).status_code == 400
    assert admin.put(user_url, json={**OPERATOR, "locationIds": [999]}).status_code == 400
    assert admin.put(user_url, json={**OPERATOR, "role": "admin"}).status_code == 400
    assert admin.put(user_url, json={**OPERATOR, "username": "admin-demo"}).status_code == 409
    assert created.json in admin.get(url).json["users"]


def test_admin_role_edits_apply_to_existing_session(app, login):
    admin = app.test_client()
    other = app.test_client()
    login(admin)
    url = "/api/admin/users"
    assert admin.put(f"{url}/1", json={
        "username": "admin-demo", "role": "operator", "locationIds": [],
    }).status_code == 409
    created = admin.post(url, json={**OPERATOR, "role": "admin", "locationIds": []})
    assert created.status_code == 201
    assert other.post("/api/session", json={
        "username": OPERATOR["username"], "password": OPERATOR["password"],
    }).status_code == 200
    assert other.get(url).status_code == 200
    assert admin.put(f"{url}/{created.json['id']}", json=OPERATOR).status_code == 200
    assert other.get(url).status_code == 403
    assert other.post(url, json=OPERATOR).status_code == 403
    assert other.put(f"{url}/1", json=OPERATOR).status_code == 403
    assert other.get("/api/inventory/locations/2").status_code == 403
