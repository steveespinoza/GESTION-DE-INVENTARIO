import re
from threading import Thread

import psycopg
import pytest
from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server


@pytest.fixture
def browser_page(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(base_url=f"http://127.0.0.1:{server.server_port}")
                yield page
            finally:
                browser.close()
    finally:
        server.shutdown()
        server_thread.join()
        server.server_close()


def test_inventory_flow(browser_page, demo_password):
    page = browser_page
    page.goto("/")
    page.get_by_label("Usuario", exact=True).fill("admin-demo")
    page.get_by_label("Contraseña", exact=True).fill(demo_password)
    page.get_by_role("button", name="Ingresar", exact=True).click()

    modules = page.get_by_role("navigation", name="Módulos")
    location = page.get_by_role("combobox", name="Ubicación", exact=True)
    form = page.get_by_role("form", name="Registrar movimiento")
    kind = form.get_by_role("combobox", name=re.compile(r"^Tipo de movimiento"))
    quantity = form.get_by_label("Cantidad", exact=True)
    stock = page.get_by_role("region", name="Stock actual")
    history = page.get_by_role("region", name="Historial de movimientos")

    expect(stock).to_be_visible()
    expect(form).to_have_count(0)
    expect(history).to_have_count(0)
    modules.get_by_role("button", name="Registrar movimiento").click()
    location.select_option(label="Almacén A")
    form.get_by_role("combobox", name=re.compile(r"^Producto")).select_option(
        label="Cable eléctrico · MAT-001 · m"
    )
    quantity.fill("100")
    form.get_by_role("button", name="Registrar entrada", exact=True).click()
    expect(page.get_by_text(re.compile(r"^Entrada #\d+ registrada\.$"))).to_be_visible()
    modules.get_by_role("button", name="Stock").click()
    expect(stock.get_by_role("cell", name="100 m", exact=True)).to_be_visible()

    modules.get_by_role("button", name="Traslados").click()
    transfer = page.get_by_role("form", name="Registrar traslado")
    expect(form).to_have_count(0)
    transfer.get_by_role("combobox", name="Ubicación de destino", exact=True).select_option(
        label="Almacén B"
    )
    transfer.get_by_role("combobox", name=re.compile(r"^Producto")).select_option(
        label="Cable eléctrico · MAT-001 · m"
    )
    transfer.get_by_label("Cantidad", exact=True).fill("30")
    transfer.get_by_role("button", name="Registrar traslado", exact=True).click()
    expect(page.get_by_text(re.compile(r"^Traslado #\d+ registrado\.$"))).to_be_visible()
    modules.get_by_role("button", name="Stock").click()
    expect(stock.get_by_role("cell", name="70 m", exact=True)).to_be_visible()
    modules.get_by_role("button", name="Historial").click()
    expect(stock).to_have_count(0)
    views = history.get_by_role("navigation", name="Vistas del historial")
    expect(history.get_by_role("cell", name="Entrada", exact=True)).to_be_visible()
    views.get_by_role("button", name="Traslados", exact=True).click()
    origin_transfer = history.get_by_role("row").filter(has_text="Traslado #")
    expect(origin_transfer.get_by_role("cell", name="-30 m", exact=True)).to_be_visible()
    expect(history.get_by_role("cell", name="Entrada", exact=True)).to_have_count(0)
    transfer_label = origin_transfer.get_by_role("cell", name=re.compile(r"^Traslado #\d+$")).inner_text()

    location.select_option(label="Almacén B")
    destination_transfer = history.get_by_role("row").filter(
        has=page.get_by_role("cell", name=transfer_label, exact=True)
    )
    expect(destination_transfer.get_by_role("cell", name="+30 m", exact=True)).to_be_visible()

    modules.get_by_role("button", name="Registrar movimiento").click()
    kind.select_option(label="Salida")
    form.get_by_role("combobox", name=re.compile(r"^Producto")).select_option(
        label="Cable eléctrico · MAT-001 · m"
    )
    quantity.fill("10")
    form.get_by_role("button", name="Registrar salida", exact=True).click()
    expect(page.get_by_text(re.compile(r"^Salida #\d+ registrada\.$"))).to_be_visible()

    quantity.fill("21")
    form.get_by_role("button", name="Registrar salida", exact=True).click()
    expect(page.get_by_role("alert")).to_have_text("Stock insuficiente para registrar la salida.")
    modules.get_by_role("button", name="Stock").click()
    expect(stock.get_by_role("cell", name="20 m", exact=True)).to_be_visible()
    modules.get_by_role("button", name="Historial").click()
    views.get_by_role("button", name="Salidas", exact=True).click()
    expect(history.get_by_role("cell", name="-10 m", exact=True)).to_be_visible()
    expect(history.get_by_role("row")).to_have_count(2)
    expect(history.get_by_role("cell", name=transfer_label, exact=True)).to_have_count(0)

    modules.get_by_role("button", name="Stock").click()
    location.select_option(label="Almacén A")
    expect(stock.get_by_role("cell", name="70 m", exact=True)).to_be_visible()

    page.locator(".sidebar").get_by_role("button", name="Cerrar sesión").click()
    page.get_by_label("Usuario", exact=True).fill("operador-demo")
    page.get_by_label("Contraseña", exact=True).fill(demo_password)
    page.get_by_role("button", name="Ingresar", exact=True).click()
    for section in ("Productos", "Ubicaciones", "Usuarios"):
        expect(modules.get_by_role("button", name=section, exact=True)).to_have_count(0)
    modules.get_by_role("button", name="Traslados").click()
    expect(page.get_by_text("Necesitas acceso a dos ubicaciones para registrar un traslado.")).to_be_visible()
    expect(transfer).to_have_count(0)

    page.set_viewport_size({"width": 390, "height": 844})
    menu = page.get_by_role("button", name="Menú", exact=True)
    expect(modules).to_be_hidden()
    menu.click()
    modules.get_by_role("button", name="Stock").click()
    expect(modules).to_be_hidden()
    expect(stock.get_by_role("cell", name="20 m", exact=True)).to_be_visible()


def test_search_across_inventory_modules(app, browser_page, demo_password):
    with psycopg.connect(app.config["DATABASE_URL"]) as connection:
        connection.execute("""
            WITH inserted AS (
                INSERT INTO movements (kind, actor_id, movement_date, reference)
                SELECT 'receipt', 1, DATE '2026-11-13', 'PAG-' || n
                FROM generate_series(1, 21) AS n
                RETURNING id
            )
            INSERT INTO movement_details (movement_id, product_id, location_id, quantity)
            SELECT id, 1, 1, 1 FROM inserted
        """)
        connection.execute("INSERT INTO stock VALUES (1, 1, 21)")

    page = browser_page
    page.goto("/")
    page.get_by_label("Usuario", exact=True).fill("admin-demo")
    page.get_by_label("Contraseña", exact=True).fill(demo_password)
    page.get_by_role("button", name="Ingresar", exact=True).click()
    modules = page.get_by_role("navigation", name="Módulos")
    expect(page.get_by_role("heading", name="Stock actual", level=1)).to_be_visible()
    page.get_by_role("searchbox", name="Buscar en stock").fill("MAT-001")
    expect(page.get_by_role("cell", name="MAT-001", exact=True)).to_be_visible()

    for section, term, result in (
        ("Productos", "mat-002", "MAT-002"),
        ("Ubicaciones", "Almacén B", "Almacén B"),
        ("Usuarios", "operador", "operador-demo"),
    ):
        modules.get_by_role("button", name=section, exact=True).click()
        page.get_by_role("searchbox", name=f"Buscar {section.lower()}").fill(term)
        expect(page.get_by_role("cell", name=result, exact=True)).to_be_visible()
        expect(page.get_by_role("row")).to_have_count(2)

    modules.get_by_role("button", name="Registrar movimiento").click()
    page.get_by_role("searchbox", name="Buscar producto").fill("MAT-002")
    product = page.get_by_role("combobox", name="Producto", exact=True)
    expect(product.locator("option")).to_have_count(2)
    expect(product.locator("option").nth(1)).to_contain_text("MAT-002")

    modules.get_by_role("button", name="Historial").click()
    history = page.get_by_role("region", name="Historial de movimientos")
    pagination = history.get_by_role("navigation", name="Paginación")
    expect(history.get_by_role("row")).to_have_count(21)
    expect(history.get_by_role("cell", name="PAG-1", exact=True)).to_have_count(0)
    search = history.get_by_role("searchbox", name="Buscar movimientos")
    search.fill("pag-1")
    history.get_by_role("button", name="Filtrar").click()
    expect(history.get_by_role("cell", name="PAG-1", exact=True)).to_be_visible()
    expect(history.get_by_role("row")).to_have_count(12)
    search.clear()
    history.get_by_role("button", name="Filtrar").click()
    expect(history.get_by_role("row")).to_have_count(21)
    pagination.get_by_role("button", name="Siguiente").click()
    expect(history.get_by_role("cell", name="PAG-1", exact=True)).to_be_visible()
    expect(history.get_by_role("row")).to_have_count(2)
    expect(pagination.get_by_role("button", name="Siguiente")).to_be_disabled()
    views = history.get_by_role("navigation", name="Vistas del historial")
    views.get_by_role("button", name="Salidas", exact=True).click()
    expect(history.get_by_text("No hay movimientos para esta consulta.")).to_be_visible()
    views.get_by_role("button", name="Entradas", exact=True).click()
    expect(history.get_by_role("row")).to_have_count(21)
    pagination.get_by_role("button", name="Siguiente").click()
    expect(history.get_by_role("row")).to_have_count(2)
    history.get_by_role("button", name="Filtrar").click()
    expect(history.get_by_role("row")).to_have_count(21)
    expect(pagination.get_by_role("button", name="Anterior")).to_be_disabled()
