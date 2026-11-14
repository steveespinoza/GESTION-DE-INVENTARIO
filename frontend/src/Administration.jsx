import { useEffect, useState } from 'react';
import { request } from './api';
import { Pagination, useTablePage } from './Pagination';
import { matchesSearch } from './search';

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
  users: {
    title: 'Usuarios',
    singular: 'usuario',
    fields: [{ key: 'username', label: 'Usuario', limit: 80 }],
  },
};

function UserFields({ editing, locations }) {
  const [role, setRole] = useState(editing?.role ?? 'operator');
  return (
    <>
      {!editing && (
        <label>Contraseña
          <input name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={256} />
          <span className="muted">Al menos 12 caracteres.</span>
        </label>
      )}
      <label>Rol
        <select name="role" value={role} onChange={(event) => setRole(event.target.value)}>
          <option value="operator">Operador</option>
          <option value="admin">Administrador</option>
        </select>
      </label>
      {role === 'operator' && (
        <fieldset className="location-assignments">
          <legend>Ubicaciones asignadas</legend>
          {locations.length === 0 && <p className="muted">Aún no hay ubicaciones.</p>}
          {locations.map(({ id, name }) => (
            <label key={id} className="location-option">
              <input type="checkbox" name="locationIds" value={id} defaultChecked={editing?.locationIds.includes(id)} />
              {name}
            </label>
          ))}
        </fieldset>
      )}
    </>
  );
}

function ResourceEditor({ resource, onExpired }) {
  const { title, singular, fields } = resources[resource];
  const endpoint = `/admin/${resource}`;
  const [items, setItems] = useState(null);
  const [search, setSearch] = useState('');
  const [locations, setLocations] = useState([]);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [formVersion, setFormVersion] = useState(0);
  const formTitle = editing ? `Editar ${singular}` : `Crear ${singular}`;
  const isUsers = resource === 'users';
  function locationNames(item) {
    if (item.role === 'admin') return 'Todas';
    return locations.filter((location) => item.locationIds.includes(location.id))
      .map((location) => location.name).join(', ') || 'Sin asignar';
  }

  const matches = (items ?? []).filter((item) => matchesSearch(search, [
    ...fields.map(({ key }) => item[key]),
    ...(isUsers ? [item.role === 'admin' ? 'Administrador' : 'Operador', locationNames(item)] : []),
  ]));
  const { page, pageCount, setPage, rows } = useTablePage(matches);

  useEffect(() => {
    const controller = new AbortController();
    request(endpoint, { signal: controller.signal })
      .then((data) => {
        setItems(data[resource]);
        if (data.locations && resource === 'users') setLocations(data.locations);
      })
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
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(form);
    if (isUsers) body.locationIds = form.getAll('locationIds').map(Number);
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const saved = await request(editing ? `${endpoint}/${editing.id}` : endpoint, {
        method: editing ? 'PUT' : 'POST',
        body,
      });
      const label = (item) => item.name ?? item.username;
      setItems((current) => [
        ...current.filter((item) => item.id !== saved.id), saved,
      ].sort((first, second) => label(first).localeCompare(label(second), 'es') || first.id - second.id));
      setEditing(null);
      setFormVersion((version) => version + 1);
      setNotice(`Se guardó «${label(saved)}».`);
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
            {isUsers && <UserFields editing={editing} locations={locations} />}
            {error && items && <p className="notice error" role="alert">{error}</p>}
            <button className="primary">{busy ? 'Guardando…' : formTitle}</button>
            {editing && <button type="button" className="secondary" onClick={() => select(null)}>Cancelar edición</button>}
          </fieldset>
        </form>
        <section className="panel" aria-labelledby="resource-title">
          <h2 id="resource-title" className="visually-hidden">{title}</h2>
          <label className="table-search">Buscar {title.toLowerCase()}
            <input type="search" value={search} onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }} />
          </label>
          {!items && !error && <p className="empty" role="status">Cargando…</p>}
          {items?.length === 0 && <p className="empty">La lista está vacía.</p>}
          {items?.length > 0 && matches.length === 0 && <p className="empty">No hay resultados para esta búsqueda.</p>}
          {rows.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr>{fields.map(({ key, label }) => <th key={key}>{label}</th>)}
                  {isUsers && <><th>Rol</th><th>Ubicaciones</th></>}
                  <th>Acción</th></tr></thead>
                <tbody>
                  {rows.map((item) => (
                    <tr key={item.id}>
                      {fields.map(({ key }) => <td key={key}>{item[key]}</td>)}
                      {isUsers && (
                        <>
                          <td>{item.role === 'admin' ? 'Administrador' : 'Operador'}</td>
                          <td>{locationNames(item)}</td>
                        </>
                      )}
                      <td><button type="button" className="secondary" disabled={busy} onClick={() => select(item)}
                        aria-label={`Editar ${item.name ?? item.username}`}>Editar</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Pagination page={page} pageCount={pageCount} onChange={setPage} />
        </section>
      </div>
    </>
  );
}

export function Administration({ resource, onExpired }) {
  return (
    <main className="workspace">
      <div className="workspace-heading"><h1>{resources[resource].title}</h1></div>
      <ResourceEditor key={resource} resource={resource} onExpired={onExpired} />
    </main>
  );
}
