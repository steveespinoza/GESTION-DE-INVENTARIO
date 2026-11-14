import re
from threading import Thread

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

    location = page.get_by_role("combobox", name=re.compile(r"^Ubicación(?! de destino)"))
    form = page.get_by_role("form", name="Registrar movimiento")
    kind = form.get_by_role("combobox", name=re.compile(r"^Tipo de movimiento"))
    quantity = form.get_by_label("Cantidad", exact=True)
    stock = page.get_by_role("region", name="Stock actual")
    history = page.get_by_role("region", name="Historial de movimientos")

    location.select_option(label="Almacén A")
    form.get_by_role("combobox", name=re.compile(r"^Producto")).select_option(
        label="Cable eléctrico · MAT-001 · m"
    )
    quantity.fill("100")
    form.get_by_role("button", name="Registrar entrada", exact=True).click()
    expect(stock.get_by_role("cell", name="100 m", exact=True)).to_be_visible()

    kind.select_option(label="Traslado")
    form.get_by_role("combobox", name=re.compile(r"^Ubicación de destino")).select_option(
        label="Almacén B"
    )
    quantity.fill("30")
    form.get_by_role("button", name="Registrar traslado", exact=True).click()
    expect(stock.get_by_role("cell", name="70 m", exact=True)).to_be_visible()
    origin_transfer = history.get_by_role("row").filter(has_text="Traslado #")
    expect(origin_transfer.get_by_role("cell", name="-30 m", exact=True)).to_be_visible()
    transfer_label = origin_transfer.get_by_role("cell", name=re.compile(r"^Traslado #\d+$")).inner_text()

    location.select_option(label="Almacén B")
    expect(stock.get_by_role("cell", name="30 m", exact=True)).to_be_visible()
    destination_transfer = history.get_by_role("row").filter(
        has=page.get_by_role("cell", name=transfer_label, exact=True)
    )
    expect(destination_transfer.get_by_role("cell", name="+30 m", exact=True)).to_be_visible()

    kind.select_option(label="Salida")
    quantity.fill("10")
    form.get_by_role("button", name="Registrar salida", exact=True).click()
    expect(stock.get_by_role("cell", name="20 m", exact=True)).to_be_visible()
    expect(history.get_by_role("cell", name="-10 m", exact=True)).to_be_visible()

    quantity.fill("21")
    form.get_by_role("button", name="Registrar salida", exact=True).click()
    expect(page.get_by_role("alert")).to_have_text("Stock insuficiente para registrar la salida.")
    expect(stock.get_by_role("cell", name="20 m", exact=True)).to_be_visible()
    expect(history.get_by_role("row")).to_have_count(3)

    location.select_option(label="Almacén A")
    expect(stock.get_by_role("cell", name="70 m", exact=True)).to_be_visible()
