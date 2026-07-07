import React from "react";

/**
 * Rank-up decree — an art-deco award certificate. Distinct from the game's
 * poster scene and cyberpunk panels: cream paper, a fine double-rule brass
 * frame with corner ticks, centered engraved typography, and a brass wax seal.
 */
export function RankUpEffect({
  eyebrow = "辞 令 · Décret",
  title = "昇格",
  body = "貴殿の捜査手腕を認め、下記の通り任ずる。",
  from,
  to,
  unlocks = [],
}) {
  const corner = {
    position: "absolute",
    width: 14,
    height: 14,
    borderColor: "var(--brass-600)",
    borderStyle: "solid",
  };
  return (
    <div
      style={{
        position: "relative",
        width: 460,
        maxWidth: "100%",
        background: "linear-gradient(180deg, var(--sepia-100), var(--poster-cream))",
        color: "var(--poster-black)",
        boxShadow: "var(--shadow-panel)",
        padding: "var(--space-8) var(--space-8) var(--space-6)",
        border: "1px solid var(--brass-600)",
        fontFamily: "var(--font-ui)",
        textAlign: "center",
      }}
    >
      {/* deco double-rule frame */}
      <div style={{ position: "absolute", inset: 10, border: "1px solid var(--brass-600)", pointerEvents: "none" }} />
      <div style={{ position: "absolute", inset: 14, border: "1px solid rgba(138,109,47,.4)", pointerEvents: "none" }} />
      {/* corner ticks */}
      <span style={{ ...corner, top: 6, left: 6, borderWidth: "2px 0 0 2px" }} />
      <span style={{ ...corner, top: 6, right: 6, borderWidth: "2px 2px 0 0" }} />
      <span style={{ ...corner, bottom: 6, left: 6, borderWidth: "0 0 2px 2px" }} />
      <span style={{ ...corner, bottom: 6, right: 6, borderWidth: "0 2px 2px 0" }} />

      <div style={{ position: "relative" }}>
        <div style={{ fontFamily: "var(--font-accent)", fontSize: "var(--text-xs)", letterSpacing: ".28em", textTransform: "uppercase", color: "var(--brass-600)" }}>{eyebrow}</div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "var(--space-3)", margin: "var(--space-3) 0" }}>
          <span style={{ flex: 1, height: 1, background: "linear-gradient(90deg, transparent, var(--brass-600))" }} />
          <span style={{ fontFamily: "var(--font-display)", fontWeight: "var(--weight-bold)", fontSize: "var(--text-2xl)", letterSpacing: ".04em", color: "var(--poster-black)" }}>{title}</span>
          <span style={{ flex: 1, height: 1, background: "linear-gradient(270deg, transparent, var(--brass-600))" }} />
        </div>
        <p style={{ fontSize: "var(--text-sm)", lineHeight: "var(--leading-relaxed)", color: "var(--sepia-900)", margin: 0 }}>{body}</p>

        {(from || to) && (
          <div style={{ margin: "var(--space-4) 0 var(--space-2)", fontFamily: "var(--font-mono)", fontSize: "var(--text-base)", color: "var(--poster-black)" }}>
            {from} <span style={{ color: "var(--copper-600)", fontWeight: "var(--weight-bold)" }}>→ {to}</span>
          </div>
        )}

        {unlocks.length > 0 && (
          <>
            <p style={{ fontFamily: "var(--font-accent)", fontSize: "var(--text-xs)", letterSpacing: ".2em", textTransform: "uppercase", color: "var(--sepia-700)", margin: "var(--space-4) 0 var(--space-3)" }}>Nouvelles commandes</p>
            <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "center", flexWrap: "wrap" }}>
              {unlocks.map((u, i) => (
                <span key={i} style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)", padding: "4px var(--space-3)", background: "transparent", color: "var(--sepia-900)", border: "1px solid var(--brass-600)" }}>{u}</span>
              ))}
            </div>
          </>
        )}

        {/* brass wax seal */}
        <div style={{ margin: "var(--space-5) auto 0", width: 40, height: 40, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: "radial-gradient(circle at 35% 30%, var(--brass-400), var(--brass-600))", color: "var(--sepia-900)", fontSize: 20, boxShadow: "var(--glow-brass), inset 0 0 6px rgba(0,0,0,.4)" }} aria-hidden="true">⚙</div>
      </div>
    </div>
  );
}
