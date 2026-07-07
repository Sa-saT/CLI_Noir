import React from "react";

/**
 * Command explainer card — shows a command's real-PC meaning and its in-game
 * meaning side by side. Steampunk brass-trimmed panel, cyan neon command name.
 */
export function CommandDetail({ name, syntax, real, inGame }) {
  return (
    <div
      style={{
        width: "var(--rail-command-w)",
        maxWidth: "100%",
        background: "var(--hairline-scan), linear-gradient(180deg, var(--gray-800), var(--gray-900))",
        border: "1px solid var(--brass-600)",
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-card), var(--bezel-brass)",
        padding: "var(--space-4)",
        fontFamily: "var(--font-ui)",
      }}
    >
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-lg)",
          color: "var(--cyan-400)",
          fontWeight: "var(--weight-bold)",
          margin: "0 0 2px",
          textShadow: "0 0 8px rgba(34,211,238,.4)",
        }}
      >
        {name}
      </p>
      {syntax && (
        <p style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--text-muted)", marginBottom: "var(--space-3)" }}>
          {syntax}
        </p>
      )}
      {real && (
        <div style={{ marginTop: "var(--space-3)" }}>
          <div style={labelStyle(false)}>実際のPCでは</div>
          <p style={bodyStyle}>{real}</p>
        </div>
      )}
      {inGame && (
        <div style={{ marginTop: "var(--space-3)" }}>
          <div style={labelStyle(true)}>この事件では</div>
          <p style={bodyStyle}>{inGame}</p>
        </div>
      )}
    </div>
  );
}

const labelStyle = (game) => ({
  fontSize: "var(--text-xs)",
  letterSpacing: "var(--tracking-caps)",
  textTransform: "uppercase",
  color: game ? "var(--term-warn)" : "var(--text-faint)",
  marginBottom: "2px",
});

const bodyStyle = {
  fontSize: "var(--text-sm)",
  lineHeight: "var(--leading-relaxed)",
  color: "var(--text-body)",
  margin: 0,
};
