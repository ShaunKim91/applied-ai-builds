import React, { useRef } from "react";

/**
 * A genuine spatial-depth interaction: as the pointer moves across the
 * card, it tilts on the X/Y axes toward the cursor (a real `perspective` +
 * `rotateX/rotateY` transform, not a shadow trick) and relaxes back to flat
 * on pointer-leave. Reserved for a few hero surfaces (the composer, stat
 * cards) rather than applied everywhere — interface-craft's "spend your
 * boldness in one place" principle; every trace card tilting on hover would
 * read as gimmicky rather than purposeful.
 *
 * Respects prefers-reduced-motion via index.css's global override (which
 * forces .tilt-card's transform to none), so no JS-side check is needed
 * here — the CSS handles the accessibility fallback uniformly.
 */
export function TiltCard({
  children,
  className = "",
  maxDeg = 6,
}: {
  children: React.ReactNode;
  className?: string;
  maxDeg?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    el.style.setProperty("--rx", `${(px * maxDeg * 2).toFixed(2)}deg`);
    el.style.setProperty("--ry", `${(-py * maxDeg * 2).toFixed(2)}deg`);
  };

  const onPointerLeave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
  };

  return (
    <div className="tilt-stage">
      <div ref={ref} onPointerMove={onPointerMove} onPointerLeave={onPointerLeave} className={`tilt-card ${className}`}>
        {children}
      </div>
    </div>
  );
}
