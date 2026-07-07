import React from "react";

/**
 * The upper story scene — CLI_Noir's first-class "current image" area. Each
 * scene shows a full-bleed copperplate/pen-ink illustration (object-fit: cover)
 * as the ground; the poster caption band, Scène badge and optional event card
 * are overlaid ON TOP of it. When no `image` is given it falls back to the
 * poster-gradient placeholder. Supports an 0.8s cross-fade for local⇄remote
 * transitions (ssh in / exit out).
 */
export function SceneOverlay({ caption, badge, event, image, fading = false, height = 320 }) {
  const [shown, setShown] = React.useState(image);
  const [visible, setVisible] = React.useState(true);

  // Cross-fade whenever the image URL changes (or `fading` is toggled).
  React.useEffect(() => {
    if (image === shown) return;
    setVisible(false); // fade out current
    const t = setTimeout(() => { setShown(image); setVisible(true); }, 800);
    return () => clearTimeout(t);
  }, [image, shown]);

  return (
    <div
      style={{
        position: "relative",
        height,
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        border: "1px solid var(--brass-600)",
        boxShadow: "var(--bezel-brass)",
        // Placeholder ground (used when no image, and shows through during fades)
        background:
          "radial-gradient(110% 80% at 72% 30%, rgba(217,165,33,.22), transparent 55%), linear-gradient(155deg, var(--poster-blue) 0%, var(--poster-black) 62%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-ui)",
      }}
    >
      {/* Scene image ground (cross-fades). Falls back to poster placeholder when absent. */}
      {shown ? (
        <img
          src={shown}
          alt=""
          aria-hidden="true"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: visible && !fading ? 1 : 0,
            transition: "opacity 0.8s ease",
            zIndex: 0,
          }}
        />
      ) : (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            top: "-10%",
            left: "-8%",
            width: "55%",
            height: "120%",
            background: "var(--poster-red)",
            transform: "skewX(-10deg)",
            opacity: 0.9,
            WebkitMaskImage: "radial-gradient(circle at 20% 30%, #000 42%, transparent 43%)",
            maskImage: "radial-gradient(circle at 20% 30%, #000 42%, transparent 43%)",
            zIndex: 0,
          }}
        />
      )}

      {/* Legibility scrim over photographic scenes */}
      {shown && (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 1,
            background: "linear-gradient(180deg, rgba(20,16,12,.35) 0%, transparent 30%, rgba(20,16,12,.45) 100%)",
            pointerEvents: "none",
          }}
        />
      )}

      {badge && (
        <span style={{ position: "absolute", top: "var(--space-5)", right: "var(--space-5)", zIndex: 3, fontFamily: "var(--font-accent)", fontWeight: "var(--weight-semibold)", textTransform: "uppercase", letterSpacing: "var(--tracking-hero)", fontSize: "var(--text-xs)", color: "var(--poster-cream)", border: "1px solid var(--poster-cream)", padding: "4px var(--space-3)" }}>
          {badge}
        </span>
      )}
      {caption && (
        <div style={{ position: "absolute", top: "var(--space-4)", left: "var(--space-4)", zIndex: 3, background: "var(--poster-cream)", color: "var(--poster-black)", padding: "var(--space-2) var(--space-4)", fontFamily: "var(--font-hero)", fontWeight: "var(--weight-medium)", fontSize: "var(--text-base)", letterSpacing: ".02em", maxWidth: "60%", boxShadow: "4px 4px 0 var(--poster-red)" }}>
          {caption}
        </div>
      )}
      {event && (
        <div style={{ position: "relative", zIndex: 2, width: "74%", maxWidth: 420, background: "var(--poster-cream)", borderRadius: 2, boxShadow: "8px 8px 0 rgba(0,0,0,.4)", padding: "var(--space-5)", color: "var(--poster-black)" }}>
          <h2 style={{ fontFamily: "var(--font-hero)", fontWeight: "var(--weight-bold)", textTransform: "uppercase", letterSpacing: "var(--tracking-hero)", fontSize: "var(--text-xl)", color: "var(--poster-red)", margin: "0 0 var(--space-2)" }}>
            {event.title}
          </h2>
          <p style={{ fontFamily: "var(--font-ui)", fontSize: "var(--text-sm)", lineHeight: "var(--leading-relaxed)", margin: 0 }}>{event.body}</p>
        </div>
      )}
    </div>
  );
}
