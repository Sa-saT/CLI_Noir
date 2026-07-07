import React from "react";

/**
 * Poster-style mission title band — 60s French film-poster treatment: black
 * ground, skewed red cut-out, Jost hero title, Josefin accent tag, brass rank chip.
 */
export function MissionHeader({ tag = "Mission 1", title, subtitle, rank }) {
  return (
    <header
      style={{
        position: "relative",
        overflow: "hidden",
        background: "var(--poster-black)",
        padding: "var(--space-5) var(--space-6)",
        borderBottom: "2px solid var(--poster-red)",
        boxShadow: "var(--shadow-panel)",
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "space-between",
        gap: "var(--space-4)",
      }}
    >
      <div style={{ position: "absolute", top: "-20%", left: "-4%", width: 120, height: "140%", background: "var(--poster-red)", transform: "skewX(-12deg)", opacity: 0.9 }} />
      <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ fontFamily: "var(--font-accent)", fontSize: "var(--text-xs)", letterSpacing: "var(--tracking-hero)", textTransform: "uppercase", fontWeight: "var(--weight-medium)", color: "var(--poster-mustard)" }}>
          {tag}
        </span>
        <h1 style={{ fontFamily: "var(--font-hero)", fontWeight: "var(--weight-bold)", fontSize: "2.5rem", textTransform: "uppercase", letterSpacing: "var(--tracking-hero)", color: "var(--poster-cream)", margin: 0, lineHeight: 0.95 }}>
          {title}
        </h1>
        {subtitle && <span style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-base)", color: "var(--poster-red)", background: "var(--poster-black)", padding: "1px 8px", alignSelf: "flex-start", boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone" }}>{subtitle}</span>}
      </div>
      {rank && (
        <span style={{ position: "relative", fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", letterSpacing: "var(--tracking-caps)", color: "var(--brass-400)", border: "1px solid var(--brass-600)", borderRadius: "var(--radius-sm)", boxShadow: "var(--glow-brass)", padding: "3px var(--space-2)", whiteSpace: "nowrap", background: "rgba(201,162,75,.06)" }}>
          {rank}
        </span>
      )}
    </header>
  );
}
