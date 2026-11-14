import { useState } from 'react';

export const PAGE_SIZE = 20;

export function useTablePage(items) {
  const [requestedPage, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const page = Math.min(requestedPage, pageCount);
  const start = (page - 1) * PAGE_SIZE;
  return {
    page,
    pageCount,
    setPage,
    rows: items.slice(start, start + PAGE_SIZE),
  };
}

export function Pagination({ page, pageCount, hasMore, onChange }) {
  const canAdvance = pageCount === undefined ? hasMore : page < pageCount;
  if (page === 1 && !canAdvance) return null;

  return (
    <nav className="pagination" aria-label="Paginación">
      <button type="button" className="secondary" disabled={page === 1}
        onClick={() => onChange(page - 1)}>Anterior</button>
      <span aria-live="polite">
        Página {page}{pageCount !== undefined && ` de ${pageCount}`}
      </span>
      <button type="button" className="secondary" disabled={!canAdvance}
        onClick={() => onChange(page + 1)}>Siguiente</button>
    </nav>
  );
}
