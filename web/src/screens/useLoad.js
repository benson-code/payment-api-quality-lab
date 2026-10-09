import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../api.js';
import { messageFor } from '../messages.js';

// Load data for a screen: { data, error, reload }.
export function useLoad(load, deps) {
  const [state, setState] = useState({ data: null, error: '' });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);
  const reload = useCallback(() => {
    run()
      .then(({ data }) => setState({ data, error: '' }))
      .catch((e) => setState({ data: null, error: e instanceof ApiError ? messageFor(e) : 'No answer from the server.' }));
  }, [run]);
  useEffect(reload, [reload]);
  return { ...state, reload };
}
