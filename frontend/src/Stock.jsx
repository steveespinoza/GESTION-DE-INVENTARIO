import { useState } from 'react';
import { Pagination, useTablePage } from './Pagination';
import { matchesSearch } from './search';

const numberFormat = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 3 });

export function Stock({ balances }) {
  const [search, setSearch] = useState('');
  const matches = balances.filter((item) => matchesSearch(search, [item.name, item.sku]));
  const { page, pageCount, setPage, rows } = useTablePage(matches);
  return (
    <section className="panel" aria-labelledby="stock-title">
      <div className="panel-heading">
        <h2 id="stock-title" className="visually-hidden">Stock actual</h2>
        <span className="muted">{balances.length} {balances.length === 1 ? 'producto' : 'productos'}</span>
      </div>
      <label className="table-search">Buscar en stock
        <input type="search" value={search} placeholder="Producto o SKU" onChange={(event) => {
          setSearch(event.target.value);
          setPage(1);
        }} />
      </label>
      {balances.length === 0 && <p className="empty">Aún no hay existencias en esta ubicación.</p>}
      {balances.length > 0 && matches.length === 0 && <p className="empty">No hay resultados para esta búsqueda.</p>}
      {rows.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Producto</th><th>SKU</th><th className="numeric">Disponible</th></tr></thead>
            <tbody>
              {rows.map((item) => (
                <tr key={item.productId}>
                  <td>{item.name}</td><td className="muted">{item.sku}</td>
                  <td className="numeric stock-value">{numberFormat.format(item.quantity)} <span>{item.unit}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} pageCount={pageCount} onChange={setPage} />
    </section>
  );
}
