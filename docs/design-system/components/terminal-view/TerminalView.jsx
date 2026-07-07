import React from "react";
import { Prompt } from "../prompt/Prompt.jsx";

const lineColor = {
  out: "var(--green-400)",
  error: "var(--term-error)",
  warn: "var(--term-warn)",
  system: "var(--gray-500)",
  input: "var(--green-300)",
};

/**
 * The pseudo-terminal: a scrollback of typed/echoed lines (out / error / warn
 * / system / input) plus a live input row with a blinking caret. Self-drawn —
 * no xterm.js. Cyberpunk black ground with scanlines and phosphor glow.
 */
export function TerminalView({
  lines = [],
  prompt = { user: "detective", host: "office", path: "~/desk" },
  input = "",
  height = 340,
}) {
  return (
    <div
      style={{
        position: "relative",
        background: "var(--hairline-scan), var(--surface-terminal)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-panel), inset 0 0 60px rgba(74,222,128,.04)",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-sm)",
        lineHeight: "var(--leading-term)",
        letterSpacing: "var(--tracking-term)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        height,
      }}
    >
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-3) var(--space-4)", color: "var(--term-fg)" }}>
        {lines.map((l, i) => {
          const kind = l.kind || "out";
          return (
            <div
              key={i}
              style={{
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                color: lineColor[kind],
                fontStyle: kind === "system" ? "italic" : "normal",
              }}
            >
              {l.text}
            </div>
          );
        })}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: ".5ch",
          borderTop: "1px solid var(--border-subtle)",
          padding: "var(--space-2) var(--space-4)",
          background: "rgba(255,255,255,.02)",
        }}
      >
        <Prompt user={prompt.user} host={prompt.host} path={prompt.path} hostType={prompt.hostType} />
        <span style={{ flex: 1, color: "var(--green-300)" }}>
          {input}
          <span
            style={{
              display: "inline-block",
              width: ".6ch",
              height: "1.05em",
              marginLeft: "1px",
              background: "var(--green-400)",
              boxShadow: "var(--shadow-glow-term)",
              animation: "clinoir-blink 1.1s step-end infinite",
              transform: "translateY(2px)",
            }}
          />
        </span>
        <style>{"@keyframes clinoir-blink { 50% { opacity: 0; } }"}</style>
      </div>
    </div>
  );
}
