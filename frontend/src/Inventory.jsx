import { useEffect, useState } from 'react';
import { request } from './api';

const movementLabels = { receipt: 'Entrada', opening: 'Saldo inicial', issue: 'Salida' };
const numberFormat = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 });
const variationFormat = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3, signDisplay: 'always' });
const dateFormat = new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeZone: 'UTC' });
const timestampFormat = new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short' });

function localDate() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

function MovementForm({ products, actor, busy, onSubmit }) {
  const [kind, setKind] = useState('receipt');
  const isIssue = kind === 'issue';
  const action = isIssue ? 'Registrar salida' : 'Registrar entrada';
  return (
    <form className="panel movement-form" onSubmit={onSubmit} aria-labelledby="movement-title">
      <h2 id="movement-title">Registrar movimiento</h2>
      <fieldset disabled={busy}>
        <label>Tipo de movimiento
          <select name="kind" value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="receipt">Entrada</option>
            {actor.role === 'admin' && <option value="opening">Saldo inicial</option>}
            <option value="issue">Salida</option>
          </select>
        </label>
        <label>Producto
          <select name="productId" required defaultValue="">
            <option value="" disabled>Selecciona un producto</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>{product.name} · {product.sku} · {product.unit}</option>
            ))}
          </select>
        </label>
        <div className="fields">
          <label>Cantidad<input name="quantity" inputMode="decimal" required maxLength={19} placeholder="0" /></label>
          <label>Fecha del movimiento<input type="date" name="movementDate" required defaultValue={localDate()} /></label>
        </div>
        <label>Referencia <span className="muted">(opcional)</span>
          <input name="reference" maxLength={120} placeholder={isIssue ? 'Ej. orden de entrega' : 'Ej. guía de recepción'} />
        </label>
        <button className="primary">{busy ? 'Registrando…' : action}</button>
      </fieldset>
    </form>
  );
}

function Stock({ balances }) {
  return (
    <section className="panel" aria-labelledby="stock-title">
      <div className="panel-heading">
        <h2 id="stock-title">Stock actual</h2>
        <span className="muted">{balances.length} {balances.length === 1 ? 'producto' : 'productos'}</span>
      </div>
      {balances.length === 0 ? <p className="empty">Aún no hay existencias en esta ubicación.</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Producto</th><th>SKU</th><th className="numeric">Disponible</th></tr></thead>
            <tbody>
              {balances.map((item) => (
                <tr key={item.productId}>
                  <td>{item.name}</td><td className="muted">{item.sku}</td>
                  <td className="numeric stock-value">{numberFormat.format(item.quantity)} <span>{item.unit}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function History({ movements, hasMore, onFilter }) {
  return (
    <section className="panel history" aria-labelledby="history-title">
      <div className="panel-heading"><h2 id="history-title">Historial de movimientos</h2></div>
      <form className="filters" onSubmit={onFilter} aria-label="Filtrar historial">
        <label>Desde<input type="date" name="from" /></label>
        <label>Hasta<input type="date" name="to" /></label>
        <label>Tipo
          <select name="kind">
            <option value="">Todos</option>
            <option value="receipt">Entrada</option>
            <option value="opening">Saldo inicial</option>
            <option value="issue">Salida</option>
          </select>
        </label>
        <button className="secondary">Filtrar</button>
      </form>
      {movements.length === 0 ? <p className="empty">No hay movimientos para esta consulta.</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Tipo</th><th>Producto</th><th className="numeric">Cantidad</th><th>Usuario</th><th>Referencia</th><th>Registrado</th></tr></thead>
            <tbody>
              {movements.map((item) => (
                <tr key={item.id}>
                  <td>{dateFormat.format(new Date(item.movementDate))}</td>
                  <td><span className="movement-kind">{movementLabels[item.kind]}</span></td>
                  <td>{item.product}</td>
                  <td className={`numeric stock-value${item.kind === 'issue' ? ' outgoing' : ''}`}>{variationFormat.format(item.quantity)} <span>{item.unit}</span></td>
                  <td>{item.actor}</td>
                  <td>{item.reference || '—'}</td>
                  <td>{timestampFormat.format(new Date(item.recordedAt))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {hasMore && <p className="empty">Se muestran los últimos 100 resultados. Acota las fechas para consultar otros movimientos.</p>}
    </section>
  );
}

export function Inventory({ actor, onLogout, onExpired }) {
  const [options, setOptions] = useState(null);
  const [locationId, setLocationId] = useState('');
  const [inventory, setInventory] = useState(null);
  const [filters, setFilters] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [queryError, setQueryError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    request('/inventory/options', { signal: controller.signal })
      .then((data) => {
        setOptions(data);
        setLocationId(String(data.locations[0]?.id ?? ''));
      })
      .catch((failure) => {
        if (failure.name === 'AbortError') return;
        if (failure.status === 401) onExpired();
        else setError(failure.message);
      });
    return () => controller.abort();
  }, [onExpired]);

  useEffect(() => {
    if (!locationId) return;
    const controller = new AbortController();
    setLoading(true);
    setQueryError('');
    request(`/inventory/locations/${locationId}?${filters}`, { signal: controller.signal })
      .then(setInventory)
      .catch((failure) => {
        if (failure.name === 'AbortError') return;
        if (failure.status === 401) onExpired();
        else setQueryError(failure.message);
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [locationId, filters, refresh, onExpired]);

  async function register(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const isIssue = values.kind === 'issue';
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await request(isIssue ? '/inventory/issues' : '/inventory/receipts', {
        method: 'POST',
        body: {
          ...values,
          productId: Number(values.productId),
          locationId: Number(locationId),
          quantity: values.quantity.trim().replace(',', '.'),
        },
      });
      form.elements.quantity.value = '';
      form.elements.reference.value = '';
      setNotice(`${movementLabels[values.kind]} #${result.id} ${values.kind === 'opening' ? 'registrado' : 'registrada'}.`);
      setRefresh((value) => value + 1);
    } catch (failure) {
      if (failure.status === 401) onExpired();
      else {
        setError(failure.message);
        if (isIssue && failure.status === 409) setRefresh((value) => value + 1);
      }
    } finally {
      setBusy(false);
    }
  }

  function applyFilters(event) {
    event.preventDefault();
    const query = new URLSearchParams(new FormData(event.currentTarget));
    setFilters(query.toString());
    setRefresh((value) => value + 1);
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <span className="wordmark"><span aria-hidden="true">▦</span> Inventario</span>
          <div className="user"><span>{actor.username}</span><button className="quiet" onClick={onLogout}>Cerrar sesión</button></div>
        </div>
      </header>
      <main className="workspace">
        <div className="workspace-heading">
          <h1>Inventario por ubicación</h1>
          {options?.locations.length > 0 && (
            <label className="location">Ubicación
              <select value={locationId} disabled={busy} onChange={(event) => {
                setLocationId(event.target.value);
                setInventory(null);
                setError('');
                setNotice('');
              }}>
                {options.locations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
          )}
        </div>
        {error && <p className="notice error" role="alert">{error}</p>}
        {notice && <p className="notice success" role="status">{notice}</p>}
        {queryError && <p className="notice error" role="alert">{queryError}</p>}
        {!options && !error && <p role="status">Cargando ubicaciones…</p>}
        {options?.locations.length === 0 && <p className="notice">No tienes ubicaciones asignadas.</p>}
        {locationId && (
          <div aria-busy={loading}>
            <div className="dashboard">
              <MovementForm products={options.products} actor={actor} busy={busy} onSubmit={register} />
              <Stock balances={inventory?.balances ?? []} />
            </div>
            <History movements={inventory?.movements ?? []} hasMore={inventory?.hasMore} onFilter={applyFilters} />
            {loading && <p className="muted" role="status">Actualizando inventario…</p>}
          </div>
        )}
      </main>
    </>
  );
}
