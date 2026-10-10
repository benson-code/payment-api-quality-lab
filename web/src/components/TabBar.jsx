import Icon from './Icon.jsx';

const TABS = [
  ['home', 'Home', 'home', ''],
  ['pay', 'Pay', 'send', '/pay'],
  ['history', 'History', 'history', '/history'],
];

// Figma: Tab bar (Active=Home | Pay | History). Shown on the Home and History screens; Pay opens
// the pay flow, which has its own back button instead.
export default function TabBar({ walletId, active }) {
  return (
    <nav className="tab-bar" aria-label="Main">
      {TABS.map(([id, label, icon, path]) => {
        const on = id === active;
        return (
          <a key={id} className="tab" href={`#/w/${walletId}${path}`} data-testid={`tab-${id}`}
             aria-current={on ? 'page' : undefined}>
            <Icon name={icon} />
            <span className={on ? 't-label' : 't-caption'}>{label}</span>
          </a>
        );
      })}
    </nav>
  );
}
