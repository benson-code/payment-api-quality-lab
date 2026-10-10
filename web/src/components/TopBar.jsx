import Icon from './Icon.jsx';

// Figma: Top bar (Back=True | Back=False). 56 px, title centred, back button a 44 px touch target.
// `back` is a link (a hash path); `onBack` is for a step inside one screen, such as Confirm -> Pay.
export default function TopBar({ title, back, onBack, backDisabled = false, backTestId = 'back', backLabel = 'Back' }) {
  let leading = <span />;
  if (back) {
    leading = (
      <a className="icon-button" href={back} data-testid={backTestId} aria-label={backLabel}>
        <Icon name="arrow-left" />
      </a>
    );
  } else if (onBack) {
    leading = (
      <button type="button" className="icon-button" onClick={onBack} disabled={backDisabled}
              data-testid={backTestId} aria-label={backLabel}>
        <Icon name="arrow-left" />
      </button>
    );
  }
  return (
    <header className="top-bar">
      {leading}
      <h1 className="top-bar-title t-title-md">{title}</h1>
      <span />
    </header>
  );
}
