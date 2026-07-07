import React from "react";
import { Button } from "../button/Button.jsx";

/**
 * Mission-complete celebration — emerald glow stage with a Jost stamp, a mono
 * subline (e.g. the commit that closed the case) and a next-mission CTA.
 */
export function ClearEffect({
  stamp = "Mission Complete!",
  sub,
  ctaLabel = "次のミッションへ →",
  onNext,
  height = 320,
}) {
  return (
    <div
      style={{
        position: "relative",
        height,
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        border: "1px solid var(--border-subtle)",
        background: "radial-gradient(120% 100% at 50% 40%, rgba(16,185,129,.18), var(--gray-950) 70%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-5)",
        textAlign: "center",
        fontFamily: "var(--font-ui)",
      }}
    >
      <div style={{ fontFamily: "var(--font-hero)", fontWeight: "var(--weight-bold)", textTransform: "uppercase", letterSpacing: "var(--tracking-hero)", fontSize: "var(--text-display)", color: "#6ee7b7", textShadow: "0 0 24px rgba(16,185,129,.6)" }}>
        {stamp}
      </div>
      {sub && <div style={{ color: "#a7f3d0", fontSize: "var(--text-sm)", fontFamily: "var(--font-mono)" }}>{sub}</div>}
      <Button variant="primary" size="lg" onClick={onNext}>{ctaLabel}</Button>
    </div>
  );
}
