from contextlib import contextmanager
from pathlib import Path

import click
import psycopg
from flask import current_app
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash


@contextmanager
def database():
    with psycopg.connect(
        current_app.config["DATABASE_URL"], row_factory=dict_row, connect_timeout=5
    ) as connection:
        yield connection


def register_commands(app):
    @app.cli.command("migrate")
    def migrate():
        """Aplica las migraciones pendientes."""
        with database() as connection:
            connection.execute("SELECT pg_advisory_xact_lock(327015)")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY)
            """)
            applied = {
                row["name"] for row in connection.execute("SELECT name FROM schema_migrations")
            }
            for migration in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
                if migration.name in applied:
                    continue
                connection.execute(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations (name) VALUES (%s)", (migration.name,)
                )
                click.echo(f"Aplicada {migration.name}")

    @app.cli.command("seed-demo")
    @click.option("--password", prompt="Contraseña de la demo", hide_input=True)
    def seed_demo(password):
        """Carga un catálogo y cuentas de demostración en una base local."""
        if len(password) < 12:
            raise click.ClickException("Usa al menos 12 caracteres.")
        with database() as connection:
            connection.execute("""
                INSERT INTO products (sku, name, unit, category)
                VALUES ('MAT-001', 'Cable eléctrico', 'm', 'Materiales'),
                       ('MAT-002', 'Guantes de trabajo', 'unid.', 'Protección')
                ON CONFLICT (sku) DO NOTHING
            """)
            connection.execute("""
                INSERT INTO locations (name) VALUES ('Almacén A'), ('Almacén B')
                ON CONFLICT (name) DO NOTHING
            """)
            for username, role in (("admin-demo", "admin"), ("operador-demo", "operator")):
                connection.execute("""
                    INSERT INTO users (username, password_hash, role)
                    VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING
                """, (username, generate_password_hash(password), role))
            connection.execute("""
                INSERT INTO user_locations (user_id, location_id)
                SELECT users.id, locations.id FROM users CROSS JOIN locations
                WHERE users.username = 'operador-demo' AND locations.name = 'Almacén B'
                ON CONFLICT DO NOTHING
            """)
        click.echo("Datos de demostración listos.")
