import React from "react";
import { Button } from "../button/Button.jsx";

/**
 * Save-select modal — on re-login, pick a git commit (save point) to resume
 * from. Brass-trimmed cyberpunk panel; each row shows hash, message, timestamp.
 */
export function SaveSelectModal({
  title = "セーブを選んで再開",
  subtitle,
  saves = [],
  selectedHash,
  onSelect,
  onRestart,
  onResume,
}) {
  const selected = selectedHash ?? saves[0]?.hash;
  return (
    <div
      style={{
        width: 480,
        maxWidth: "100%",
        background: "var(--hairline-scan), linear-gradient(180deg, var(--gray-800), var(--gray-900))",
        border: "1px solid var(--brass-600)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-panel), var(--bezel-brass)",
        overflow: "hidden",
        fontFamily: "var(--font-ui)",
      }}
    >
      <div style={{ padding: "var(--space-4) var(--space-5)", borderBottom: "1px solid var(--brass-600)", background: "linear-gradient(180deg, rgba(201,162,75,.08), transparent)" }}>
        <h2 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "var(--text-lg)", color: "var(--brass-400)" }}>{title}</h2>
        {subtitle && <p style={{ margin: "4px 0 0", fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>{subtitle}</p>}
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: "var(--space-2)" }}>
        {saves.map((s, i) => {
          const isSel = s.hash === selected;
          return (
            <li
              key={s.hash || i}
              onClick={() => onSelect && onSelect(s.hash)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
                padding: "var(--space-3)",
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                border: "1px solid transparent",
                ...(isSel ? { background: "rgba(99,102,241,.12)", borderColor: "var(--accent)", boxShadow: "var(--glow-indigo)" } : null),
              }}
            >
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)", color: "var(--cyan-400)" }}>{s.hash}</span>
              <span style={{ flex: 1 }}>
                <span style={{ display: "block", fontSize: "var(--text-sm)", color: "var(--text-body)" }}>{s.message}</span>
                <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-faint)", fontFamily: "var(--font-mono)" }}>{s.when}</span>
              </span>
              {s.latest && (
                <span style={{ fontSize: "var(--text-xs)", letterSpacing: "var(--tracking-caps)", color: "var(--term-warn)", border: "1px solid var(--term-warn)", borderRadius: "var(--radius-sm)", padding: "1px var(--space-2)" }}>最新</span>
              )}
            </li>
          );
        })}
      </ul>
      <div style={{ padding: "var(--space-3) var(--space-5)", display: "flex", justifyContent: "flex-end", gap: "var(--space-2)", borderTop: "1px solid var(--border-subtle)" }}>
        <Button variant="ghost" onClick={onRestart}>最初から</Button>
        <Button variant="primary" onClick={onResume}>このセーブで再開</Button>
      </div>
    </div>
  );
}
