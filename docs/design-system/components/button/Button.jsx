import React from "react";

const sizes = {
  md: { padding: "var(--space-2) var(--space-4)", fontSize: "var(--text-sm)" },
  lg: { padding: "var(--space-3) var(--space-6)", fontSize: "var(--text-base)" },
};

const variants = {
  primary: {
    base: { background: "var(--accent)", color: "#fff", boxShadow: "var(--bezel-brass), var(--glow-indigo)" },
    hover: { background: "var(--accent-hover)", boxShadow: "var(--bezel-brass), var(--glow-indigo), 0 0 28px rgba(99,102,241,.35)" },
  },
  secondary: {
    base: { background: "var(--surface-panel)", color: "var(--text-body)", borderColor: "var(--brass-600)" },
    hover: { borderColor: "var(--brass-400)", color: "var(--brass-400)", boxShadow: "var(--glow-brass)" },
  },
  ghost: {
    base: { background: "transparent", color: "var(--accent-quiet)" },
    hover: { background: "rgba(99,102,241,.12)", color: "var(--cyan-400)", textShadow: "0 0 8px rgba(34,211,238,.5)" },
  },
};

/**
 * CLI_Noir action button — cyberpunk indigo glow (primary), steampunk brass
 * trim (secondary), neon-hover ghost. Three variants × two sizes.
 */
export function Button({
  children,
  variant = "primary",
  size = "md",
  disabled = false,
  onClick,
  type = "button",
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const v = variants[variant] || variants.primary;
  const style = {
    fontFamily: "var(--font-ui)",
    fontWeight: "var(--weight-semibold)",
    letterSpacing: ".02em",
    border: "1px solid transparent",
    borderRadius: "var(--radius-md)",
    cursor: disabled ? "not-allowed" : "pointer",
    transition: "background .15s ease, border-color .15s ease, color .15s ease, box-shadow .15s ease, transform .08s ease",
    ...sizes[size],
    ...v.base,
    ...(hover && !disabled ? v.hover : null),
    ...(disabled ? { opacity: 0.4, boxShadow: "none", filter: "grayscale(.3)" } : null),
  };
  return (
    <button
      type={type}
      style={style}
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      {...rest}
    >
      {children}
    </button>
  );
}
