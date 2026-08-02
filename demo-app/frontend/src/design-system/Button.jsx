export function Button({ children, className = '', variant = 'default', ...props }) {
  const classes = ['ui-button', variant !== 'default' ? `ui-button-${variant}` : '', className]
    .filter(Boolean)
    .join(' ');
  return (
    <button className={classes} {...props}>
      {children}
    </button>
  );
}
