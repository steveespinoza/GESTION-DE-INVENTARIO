import { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { request } from './api';
import { Inventory } from './Inventory';
import './styles.css';

function Login({ onLogin }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const credentials = Object.fromEntries(new FormData(event.currentTarget));
    setError('');
    setBusy(true);
    try {
      onLogin(await request('/session', { method: 'POST', body: credentials }));
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-layout">
      <div className="login-intro">
        <span className="wordmark"><span aria-hidden="true">▦</span> Inventario</span>
        <h1>Gestión de<br />inventario</h1>
        <p>Registra entradas y salidas, y consulta las existencias de cada almacén.</p>
      </div>
      <form className="panel login-panel" onSubmit={submit}>
        <h2>Iniciar sesión</h2>
        <label>Usuario<input name="username" autoComplete="username" required maxLength={80} /></label>
        <label>Contraseña<input type="password" name="password" autoComplete="current-password" required maxLength={256} /></label>
        {error && <p className="notice error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Ingresando…' : 'Ingresar'}</button>
      </form>
    </main>
  );
}

function App() {
  const [actor, setActor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const expireSession = useCallback(() => setActor(null), []);

  useEffect(() => {
    request('/session')
      .then(setActor)
      .catch((failure) => { if (failure.status !== 401) setError(failure.message); })
      .finally(() => setLoading(false));
  }, []);

  async function logout() {
    setError('');
    try {
      await request('/session', { method: 'DELETE' });
      setActor(null);
    } catch (failure) {
      setError(failure.message);
    }
  }

  if (loading) return <main className="status-page" role="status">Cargando sesión…</main>;
  return (
    <>
      {error && <p className="notice error session-error" role="alert">{error}</p>}
      {actor
        ? <Inventory actor={actor} onLogout={logout} onExpired={expireSession} />
        : <Login onLogin={(user) => { setError(''); setActor(user); }} />}
    </>
  );
}

createRoot(document.getElementById('root')).render(<App />);
