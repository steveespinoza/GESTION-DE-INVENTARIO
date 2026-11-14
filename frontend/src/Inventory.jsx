import { useEffect, useState } from 'react';
import { request } from './api';
import { History } from './History';
import { MovementForm } from './MovementForm';
import { PAGE_SIZE } from './Pagination';
import { Stock } from './Stock';
import { movementLabels } from './movementLabels';

const movementEndpoints = {
  receipt: '/inventory/receipts', opening: '/inventory/receipts',
  issue: '/inventory/issues', transfer: '/inventory/transfers',
};
const titles = {
  stock: 'Stock actual',
  register: 'Registrar movimiento',
  transfer: 'Traslados',
  history: 'Historial de movimientos',
};

export function Inventory({ actor, section, onExpired }) {
  const [options, setOptions] = useState(null);
  const [locationId, setLocationId] = useState('');
  const [inventory, setInventory] = useState(null);
  const [filters, setFilters] = useState('');
  const [historyView, setHistoryView] = useState('incoming');
  const [historyPage, setHistoryPage] = useState(null);
  const [refresh, setRefresh] = useState(0);
  const [accessRefresh, setAccessRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null);
  const [queryError, setQueryError] = useState('');
  const origin = options?.locations.find((item) => String(item.id) === locationId);
  const destinations = options?.locations.filter((item) => item.id !== origin?.id) ?? [];
  const page = historyPage?.locationId === locationId ? historyPage.number : 1;
  const query = section === 'history'
    ? `${filters}${filters ? '&' : ''}kind=${historyView}&page=${page}&pageSize=${PAGE_SIZE}`
    : 'pageSize=1';
  const canQuery = section === 'stock' || section === 'history';
  const visibleInventory = inventory?.locationId === locationId && inventory?.query === query
    ? inventory : null;

  useEffect(() => {
    const controller = new AbortController();
    request('/inventory/options', { signal: controller.signal })
      .then((data) => {
        setOptions(data);
        setLocationId((selected) => data.locations.some((item) => String(item.id) === selected)
          ? selected : String(data.locations[0]?.id ?? ''));
      })
      .catch((failure) => {
        if (failure.name === 'AbortError') return;
        if (failure.status === 401) onExpired();
        else setError(failure.message);
      });
    return () => controller.abort();
  }, [accessRefresh, onExpired]);

  useEffect(() => {
    function refreshOnFocus() {
      setAccessRefresh((value) => value + 1);
      setRefresh((value) => value + 1);
    }
    window.addEventListener('focus', refreshOnFocus);
    return () => window.removeEventListener('focus', refreshOnFocus);
  }, []);

  useEffect(() => {
    if (!locationId || !canQuery) return;
    const controller = new AbortController();
    setLoading(true);
    setQueryError('');
    request(`/inventory/locations/${locationId}?${query}`, { signal: controller.signal })
      .then((data) => setInventory({ ...data, locationId, query }))
      .catch((failure) => {
        if (failure.name === 'AbortError') return;
        if (failure.status === 401) onExpired();
        else {
          setQueryError(failure.message);
          if (failure.status === 403) {
            setInventory(null);
            setAccessRefresh((value) => value + 1);
          }
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [locationId, canQuery, query, refresh, onExpired]);

  async function register(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const { destinationId, ...movement } = values;
    setBusy(true);
    setError('');
    setNotice(null);
    try {
      const result = await request(movementEndpoints[values.kind], {
        method: 'POST',
        body: {
          ...movement,
          ...(destinationId && { destinationId: Number(destinationId) }),
          productId: Number(values.productId),
          locationId: Number(locationId),
          quantity: values.quantity.trim().replace(',', '.'),
        },
      });
      form.elements.quantity.value = '';
      form.elements.reference.value = '';
      const participle = ['opening', 'transfer'].includes(values.kind) ? 'registrado' : 'registrada';
      setNotice({ section, text: `${movementLabels[values.kind]} #${result.id} ${participle}.` });
      setRefresh((value) => value + 1);
    } catch (failure) {
      if (failure.status === 401) onExpired();
      else {
        setError(failure.message);
        if (failure.status === 403) setAccessRefresh((value) => value + 1);
        if (failure.status === 409) setRefresh((value) => value + 1);
      }
    } finally {
      setBusy(false);
    }
  }

  function applyFilters(event) {
    event.preventDefault();
    const query = new URLSearchParams(new FormData(event.currentTarget));
    setFilters(query.toString());
    setHistoryPage(null);
    setRefresh((value) => value + 1);
  }

  return (
    <main className="workspace">
      <div className="workspace-heading">
        <h1>{titles[section]}</h1>
        {options?.locations.length > 0 && (
          <label className="location">{section === 'transfer' ? 'Ubicación de origen' : 'Ubicación'}
            <select value={locationId} disabled={busy} onChange={(event) => {
              setLocationId(event.target.value);
              setHistoryPage(null);
              setInventory(null);
              setError('');
              setNotice(null);
            }}>
              {options.locations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
        )}
      </div>
      {error && <p className="notice error" role="alert">{error}</p>}
      {notice?.section === section && <p className="notice success" role="status">{notice.text}</p>}
      {canQuery && queryError && <p className="notice error" role="alert">{queryError}</p>}
      {!options && !error && <p role="status">Cargando ubicaciones…</p>}
      {options?.locations.length === 0 && <p className="notice">No tienes ubicaciones asignadas.</p>}
      {origin && (
        <div aria-busy={canQuery && loading}>
          {section === 'stock' && visibleInventory && <Stock key={locationId} balances={visibleInventory.balances} />}
          {section === 'history' && (
            <History movements={visibleInventory?.movements} hasMore={visibleInventory?.hasMore}
              filters={filters} page={page} onFilter={applyFilters} view={historyView}
              onViewChange={(view) => {
                setHistoryView(view);
                setHistoryPage(null);
              }}
              onPageChange={(number) => setHistoryPage({ locationId, number })} />
          )}
          {section === 'register' && (
            <MovementForm key="register" products={options.products} actor={actor}
              busy={busy} onSubmit={register} />
          )}
          {section === 'transfer' && (destinations.length > 0 ? (
            <MovementForm key="transfer" products={options.products} origin={origin} destinations={destinations}
              actor={actor} isTransfer busy={busy} onSubmit={register} />
          ) : <p className="notice">Necesitas acceso a dos ubicaciones para registrar un traslado.</p>)}
          {canQuery && loading && <p className="muted" role="status">Actualizando inventario…</p>}
        </div>
      )}
    </main>
  );
}
