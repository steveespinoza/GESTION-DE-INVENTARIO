import os
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from inventory import create_app

DEMO_PASSWORD = "inventario-prueba-local"


@pytest.fixture
def app():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Configura TEST_DATABASE_URL para ejecutar las pruebas de PostgreSQL.")
    schema_name = f"test_inventory_{uuid4().hex}"
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


@pytest.fixture
def login():
    def sign_in(client, username="admin-demo"):
        result = client.post("/api/session", json={"username": username, "password": DEMO_PASSWORD})
        assert result.status_code == 200
    return sign_in
