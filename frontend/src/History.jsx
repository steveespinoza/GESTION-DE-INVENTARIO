import { movementLabels } from './movementLabels';
import { Pagination } from './Pagination';

const variationFormat = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3, signDisplay: 'always' });
const dateFormat = new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeZone: 'UTC' });
const timestampFormat = new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short' });

const views = [
  ['incoming', 'Entradas'],
  ['issue', 'Salidas'],
  ['transfer', 'Traslados'],
];

export function History({ movements, hasMore, filters, page, onFilter, onPageChange, view, onViewChange }) {
  const selectedFilters = new URLSearchParams(filters);
  return (
    <section className="panel history" aria-labelledby="history-title">
      <h2 id="history-title" className="visually-hidden">Historial de movimientos</h2>
      <nav className="history-views" aria-label="Vistas del historial">
        {views.map(([id, label]) => (
          <button key={id} type="button" className={view === id ? 'primary' : 'secondary'}
            aria-pressed={view === id} onClick={() => onViewChange(id)}>{label}</button>
        ))}
      </nav>
      <form className="filters" onSubmit={onFilter} aria-label="Filtrar historial">
        <label className="history-search">Buscar movimientos
          <input type="search" name="q" maxLength={120} defaultValue={selectedFilters.get('q') ?? ''}
            placeholder="Producto, SKU, usuario o referencia" />
        </label>
        <label>Desde<input type="date" name="from" defaultValue={selectedFilters.get('from') ?? ''} /></label>
        <label>Hasta<input type="date" name="to" defaultValue={selectedFilters.get('to') ?? ''} /></label>
        <button className="secondary">Filtrar</button>
      </form>
      {movements && (movements.length === 0 ? <p className="empty">No hay movimientos para esta consulta.</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Tipo</th><th>Producto</th><th className="numeric">Cantidad</th><th>Usuario</th><th>Referencia</th><th>Registrado</th></tr></thead>
            <tbody>
              {movements.map((item) => (
                <tr key={item.id}>
                  <td>{dateFormat.format(new Date(item.movementDate))}</td>
                  <td><span className="movement-kind">{movementLabels[item.kind]}{item.kind === 'transfer' && ` #${item.id}`}</span></td>
                  <td>{item.product}</td>
                  <td className={`numeric stock-value${item.quantity.startsWith('-') ? ' outgoing' : ''}`}>{variationFormat.format(item.quantity)} <span>{item.unit}</span></td>
                  <td>{item.actor}</td>
                  <td>{item.reference || '—'}</td>
                  <td>{timestampFormat.format(new Date(item.recordedAt))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <Pagination page={page} hasMore={hasMore} onChange={onPageChange} />
    </section>
  );
}
