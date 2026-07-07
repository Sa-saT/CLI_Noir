import React from "react";

const rowBase = {
  display: "flex",
  alignItems: "center",
  gap: "var(--space-2)",
  padding: "var(--space-2) var(--space-4)",
  fontFamily: "var(--font-mono)",
  fontSize: "var(--text-sm)",
  cursor: "default",
};

const stateStyle = {
  unlocked: { color: "var(--green-400)" },
  highlight: { color: "var(--yellow-300)", fontWeight: "var(--weight-bold)" },
  locked: { color: "var(--cmd-locked)", filter: "grayscale(1)" },
};

const stateIcon = { unlocked: "›", highlight: "★", locked: "☢" };

/**
 * Available-commands rail. Renders unlocked / highlighted / locked commands
 * with brass icons + level badges. Steampunk panel with brass bezel + scanlines.
 */
export function CommandPanel({ title = "使用可能コマンド", commands = [] }) {
  return (
    <aside
      style={{
        width: "var(--rail-command-w)",
        maxWidth: "100%",
        background: "var(--hairline-scan), linear-gradient(180deg, var(--gray-800), var(--gray-900))",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-panel), var(--bezel-brass)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          padding: "var(--space-3) var(--space-4)",
          borderBottom: "1px solid var(--brass-600)",
          background: "linear-gradient(180deg, rgba(201,162,75,.10), transparent)",
          fontFamily: "var(--font-display)",
          fontSize: "var(--text-sm)",
          fontWeight: "var(--weight-semibold)",
          color: "var(--brass-400)",
          letterSpacing: "var(--tracking-caps)",
          textTransform: "uppercase",
        }}
      >
        <span aria-hidden="true">⚙</span>
        {title}
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: "var(--space-2) 0" }}>
        {commands.map((c, i) => {
          const state = c.state || "unlocked";
          return (
            <li key={i} style={{ ...rowBase, ...stateStyle[state] }}>
              <span
                style={{
                  width: "1em",
                  textAlign: "center",
                  color: state === "locked" ? "var(--cmd-locked)" : "var(--brass-400)",
                }}
              >
                {stateIcon[state]}
              </span>
              <span>{c.name}</span>
              {c.badge && (
                <span
                  style={{
                    marginLeft: "auto",
                    fontFamily: "var(--font-ui)",
                    fontSize: "var(--text-xs)",
                    color: "var(--text-faint)",
                    letterSpacing: "var(--tracking-caps)",
                  }}
                >
                  {c.badge}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
