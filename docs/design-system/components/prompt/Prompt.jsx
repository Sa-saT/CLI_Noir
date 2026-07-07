import React from "react";

/**
 * A shell prompt line: user@host:path $ with an optional blinking caret.
 * `host` type recolors the hostname — local (grey), remote (yellow glow),
 * su (grey, different user).
 */
export function Prompt({
  user = "detective",
  host = "office",
  path = "/root/desk",
  hostType = "local",
  caret = false,
}) {
  const hostColor = hostType === "remote" ? "var(--yellow-300)" : "var(--gray-300)";
  const hostShadow = hostType === "remote" ? "0 0 8px rgba(253,224,71,.4)" : "none";
  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-sm)",
        letterSpacing: "var(--tracking-term)",
        display: "inline-flex",
        alignItems: "baseline",
        gap: ".5ch",
      }}
    >
      <span style={{ color: "var(--green-300)" }}>{user}</span>
      <span style={{ color: "var(--text-muted)" }}>@</span>
      <span style={{ color: hostColor, textShadow: hostShadow }}>{host}</span>
      <span style={{ color: "var(--text-muted)" }}>:</span>
      <span style={{ color: "var(--indigo-300)" }}>{path}</span>
      <span style={{ color: "var(--text-muted)" }}>$</span>
      {caret && (
        <span
          style={{
            display: "inline-block",
            width: ".6ch",
            height: "1.1em",
            marginLeft: ".3ch",
            background: "var(--green-400)",
            boxShadow: "var(--shadow-glow-term)",
            animation: "clinoir-blink 1.1s step-end infinite",
            transform: "translateY(2px)",
          }}
        />
      )}
      <style>{"@keyframes clinoir-blink { 50% { opacity: 0; } }"}</style>
    </span>
  );
}
