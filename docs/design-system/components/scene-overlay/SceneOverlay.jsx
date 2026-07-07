import React from "react";

/**
 * The upper story scene — a French-poster "current image" area with a cream
 * caption band and an optional centered event card. Poster palette, skewed
 * cut-out geometry, hard drop-shadows.
 */
export function SceneOverlay({ caption, badge, event, height = 320 }) {
  return (
    <div
      style={{
        position: "relative",
        height,
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        border: "1px solid var(--brass-600)",
        boxShadow: "var(--bezel-brass)",
        background: "radial-gradient(110% 80% at 72% 30%, rgba(217,165,33,.22), transparent 55%), linear-gradient(155deg, var(--poster-blue) 0%, var(--poster-black) 62%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-ui)",
      }}
    >
      <div style={{ position: "absolute", top: "-10%", left: "-8%", width: "55%", height: "120%", background: "var(--poster-red)", transform: "skewX(-10deg)", opacity: 0.9, WebkitMaskImage: "radial-gradient(circle at 20% 30%, #000 42%, transparent 43%)", maskImage: "radial-gradient(circle at 20% 30%, #000 42%, transparent 43%)" }} />
      {badge && (
        <span style={{ position: "absolute", top: "var(--space-5)", right: "var(--space-5)", zIndex: 2, fontFamily: "var(--font-accent)", fontWeight: "var(--weight-semibold)", textTransform: "uppercase", letterSpacing: "var(--tracking-hero)", fontSize: "var(--text-xs)", color: "var(--poster-cream)", border: "1px solid var(--poster-cream)", padding: "4px var(--space-3)" }}>
          {badge}
        </span>
      )}
      {caption && (
        <div style={{ position: "absolute", top: "var(--space-4)", left: "var(--space-4)", zIndex: 2, background: "var(--poster-cream)", color: "var(--poster-black)", padding: "var(--space-2) var(--space-4)", fontFamily: "var(--font-hero)", fontWeight: "var(--weight-medium)", fontSize: "var(--text-base)", letterSpacing: ".02em", maxWidth: "60%", boxShadow: "4px 4px 0 var(--poster-red)" }}>
          {caption}
        </div>
      )}
      {event && (
        <div style={{ position: "relative", zIndex: 1, width: "74%", maxWidth: 420, background: "var(--poster-cream)", borderRadius: 2, boxShadow: "8px 8px 0 rgba(0,0,0,.4)", padding: "var(--space-5)", color: "var(--poster-black)" }}>
          <h2 style={{ fontFamily: "var(--font-hero)", fontWeight: "var(--weight-bold)", textTransform: "uppercase", letterSpacing: "var(--tracking-hero)", fontSize: "var(--text-xl)", color: "var(--poster-red)", margin: "0 0 var(--space-2)" }}>
            {event.title}
          </h2>
          <p style={{ fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", lineHeight: "var(--leading-relaxed)", margin: 0 }}>{event.body}</p>
        </div>
      )}
    </div>
  );
}
