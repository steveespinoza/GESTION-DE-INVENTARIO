import { useEffect, useState } from 'react';
import { request } from './api';

const resources = {
  products: {
    title: 'Productos',
    singular: 'producto',
    fields: [
      { key: 'sku', label: 'SKU', limit: 60 },
      { key: 'name', label: 'Nombre', limit: 120 },
      { key: 'unit', label: 'Unidad de medida', limit: 30 },
      { key: 'category', label: 'Categoría', limit: 80 },
    ],
  },
  locations: {
    title: 'Ubicaciones',
    singular: 'ubicación',
    fields: [{ key: 'name', label: 'Nombre', limit: 120 }],
  },
};

function ResourceEditor({ resource, onExpired }) {
  const { title, singular, fields } = resources[resource];
  const endpoint = `/admin/${resource}`;
  const [items, setItems] = useState(null);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [formVersion, setFormVersion] = useState(0);
  const formTitle = editing ? `Editar ${singular}` : `Crear ${singular}`;

  useEffect(() => {
    const controller = new AbortController();
    request(endpoint, { signal: controller.signal })
      .then((data) => setItems(data[resource]))
      .catch((failure) => {
        if (failure.name === 'AbortError') return;
        if (failure.status === 401) onExpired();
        else setError(failure.message);
      });
    return () => controller.abort();
  }, [endpoint, resource, onExpired]);

  function select(item) {
    setEditing(item);
    setError('');
    setNotice('');
    setFormVersion((version) => version + 1);
  }

  async function save(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const saved = await request(editing ? `${endpoint}/${editing.id}` : endpoint, {
        method: editing ? 'PUT' : 'POST',
        body,
      });
      setItems((current) => [
        ...current.filter((item) => item.id !== saved.id), saved,
      ].sort((first, second) => first.name.localeCompare(second.name, 'es') || first.id - second.id));
      setEditing(null);
      setFormVersion((version) => version + 1);
      setNotice(`Se guardó «${saved.name}».`);
    } catch (failure) {
      if (failure.status === 401) onExpired();
      else setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {notice && <p className="notice success" role="status">{notice}</p>}
      {error && !items && <p className="notice error" role="alert">{error}</p>}
      <div className="dashboard">
        <form key={formVersion} className="panel movement-form" onSubmit={save} aria-labelledby="editor-title">
          <h2 id="editor-title">{formTitle}</h2>
          <fieldset disabled={busy || !items}>
            {fields.map(({ key, label, limit }) => (
              <label key={key}>{label}
                <input name={key} required maxLength={limit} defaultValue={editing?.[key] ?? ''} />
              </label>
            ))}
            {error && items && <p className="notice error" role="alert">{error}</p>}
            <button className="primary">{busy ? 'Guardando…' : formTitle}</button>
            {editing && <button type="button" className="secondary" onClick={() => select(null)}>Cancelar edición</button>}
          </fieldset>
        </form>
        <section className="panel" aria-labelledby="resource-title">
          <div className="panel-heading"><h2 id="resource-title">{title}</h2></div>
          {!items && !error && <p className="empty" role="status">Cargando…</p>}
          {items?.length === 0 && <p className="empty">La lista está vacía.</p>}
          {items?.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr>{fields.map(({ key, label }) => <th key={key}>{label}</th>)}<th>Acción</th></tr></thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      {fields.map(({ key }) => <td key={key}>{item[key]}</td>)}
                      <td><button type="button" className="secondary" disabled={busy} onClick={() => select(item)}
                        aria-label={`Editar ${item.name}`}>Editar</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </>
  );
}

export function Administration({ onExpired }) {
  const [resource, setResource] = useState('products');
  return (
    <main className="workspace">
      <div className="workspace-heading"><h1>Administración</h1></div>
      <nav className="resource-nav" aria-label="Secciones de administración">
        {Object.entries(resources).map(([key, { title }]) => (
          <button key={key} type="button" className={resource === key ? 'primary' : 'secondary'}
            aria-pressed={resource === key} onClick={() => setResource(key)}>{title}</button>
        ))}
      </nav>
      <ResourceEditor key={resource} resource={resource} onExpired={onExpired} />
    </main>
  );
}
