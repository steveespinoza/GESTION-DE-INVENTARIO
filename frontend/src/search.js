export function matchesSearch(query, values) {
  const term = query.trim().toLocaleLowerCase('es');
  return values.some((value) => value?.toLocaleLowerCase('es').includes(term));
}
