import { useState } from 'react';
import { movementLabels } from './movementLabels';
import { matchesSearch } from './search';

function localDate() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

export function MovementForm({ products, origin, destinations, actor, isTransfer, busy, onSubmit }) {
  const [kind, setKind] = useState('receipt');
  const [productSearch, setProductSearch] = useState('');
  const [productId, setProductId] = useState('');
  const matchingProducts = products.filter((product) => matchesSearch(productSearch, [product.name, product.sku]));
  const selectedProductId = matchingProducts.some((product) => String(product.id) === productId)
    ? productId : '';
  const movementKind = isTransfer ? 'transfer' : kind;
  const action = `Registrar ${movementLabels[movementKind].toLowerCase()}`;
  const title = isTransfer ? 'Registrar traslado' : 'Registrar movimiento';
  return (
    <form className="panel movement-form inventory-entry" onSubmit={onSubmit} aria-labelledby="movement-title">
      <h2 id="movement-title" className="visually-hidden">{title}</h2>
      <fieldset disabled={busy}>
        {isTransfer ? <input type="hidden" name="kind" value="transfer" /> : <label>Tipo de movimiento
          <select name="kind" value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="receipt">Entrada</option>
            {actor.role === 'admin' && <option value="opening">Saldo inicial</option>}
            <option value="issue">Salida</option>
          </select>
        </label>}
        {isTransfer && (
          <>
            <label>Ubicación de destino
              <select key={origin.id} name="destinationId" required defaultValue="">
                <option value="" disabled>Selecciona el destino</option>
                {destinations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
          </>
        )}
        <label>Buscar producto
          <input type="search" value={productSearch} placeholder="Producto o SKU"
            onChange={(event) => { setProductSearch(event.target.value); setProductId(''); }} />
        </label>
        <label>Producto
          <select name="productId" required value={selectedProductId} onChange={(event) => setProductId(event.target.value)}>
            <option value="" disabled>{matchingProducts.length ? 'Selecciona un producto' : 'No hay productos disponibles'}</option>
            {matchingProducts.map((product) => (
              <option key={product.id} value={product.id}>{product.name} · {product.sku} · {product.unit}</option>
            ))}
          </select>
        </label>
        <div className="fields">
          <label>Cantidad<input name="quantity" inputMode="decimal" required maxLength={19} placeholder="0" /></label>
          <label>Fecha del movimiento<input type="date" name="movementDate" required defaultValue={localDate()} /></label>
        </div>
        <label>Referencia <span className="muted">(opcional)</span>
          <input name="reference" maxLength={120} placeholder={kind === 'issue' || isTransfer ? 'Ej. orden de entrega' : 'Ej. guía de recepción'} />
        </label>
        <button className="primary" disabled={matchingProducts.length === 0}>{busy ? 'Registrando…' : action}</button>
      </fieldset>
    </form>
  );
}
