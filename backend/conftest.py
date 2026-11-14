import os
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from inventory import create_app

@pytest.fixture
def demo_password():
    return "inventario-prueba-local"


@pytest.fixture
def app(demo_password):
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        message = "Configura TEST_DATABASE_URL para ejecutar las pruebas de PostgreSQL."
        if os.environ.get("CI") == "true":
            pytest.fail(message)
        pytest.skip(message)
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
            for command in (["migrate"], ["migrate"], ["seed-demo", "--password", demo_password]):
                result = runner.invoke(args=command)
                assert result.exit_code == 0, result.output or repr(result.exception)
            yield app
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))


@pytest.fixture
def login(demo_password):
    def sign_in(client, username="admin-demo"):
        result = client.post("/api/session", json={"username": username, "password": demo_password})
        assert result.status_code == 200
    return sign_in
