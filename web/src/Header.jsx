import Icon from './Icon.jsx';

// The bar at the top of every screen: a back link (when there is somewhere to go back to) and a title.
export default function Header({ title, back, backTestId = 'back', backLabel = 'Back' }) {
  return (
    <header className="topbar">
      {back ? (
        <a className="topbar-back" href={back} data-testid={backTestId} aria-label={backLabel}>
          <Icon name="back" />
        </a>
      ) : (
        <span className="topbar-logo"><Icon name="wallet" size={22} /></span>
      )}
      <span className="topbar-title">{title}</span>
    </header>
  );
}
