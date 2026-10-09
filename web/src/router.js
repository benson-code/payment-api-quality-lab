import { useEffect, useState } from 'react';

// Routing by the URL hash (#/w/<wallet>/pay): no router dependency, and the server only ever serves
// index.html, so no server-side fallback route is needed.
export function useHashPath() {
  const read = () => window.location.hash.replace(/^#/, '') || '/';
  const [path, setPath] = useState(read);
  useEffect(() => {
    const onChange = () => setPath(read());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return path;
}

export function go(path) {
  window.location.hash = path;
}
