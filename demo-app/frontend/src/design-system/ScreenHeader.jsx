export function ScreenHeader({ eyebrow, title, description, action }) {
  return (
    <header className="hero compact">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </header>
  );
}
