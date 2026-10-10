import { useEffect, useRef } from 'react';
import Icon from './Icon.jsx';

const ICON = { error: 'alert-circle', warning: 'alert-circle', success: 'check-circle' };

// Figma: Message (Kind=Error | Warning | Success).
// Error: the request was refused, nothing was charged. Warning: no answer, the outcome is unknown.
// Success: a confirmation, such as a payment that had already gone through.
//
// A message scrolls itself into view when it appears (SPEC L-04): on a small phone it can otherwise
// land below the visible area, and the user sees nothing happen. Found by the Android app's Appium
// run on a 360 x 640 dp screen; the web had the same problem at a 360 x 640 viewport.
export default function Message({ kind, testId, children }) {
  const ref = useRef(null);
  useEffect(() => {
    ref.current?.scrollIntoView?.({ block: 'nearest' });
  }, [children]);
  return (
    <div ref={ref} className={`message message-${kind}`} data-testid={testId} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon name={ICON[kind]} />
      <p className="t-body">{children}</p>
    </div>
  );
}
