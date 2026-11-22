/**
 * A smiling card character in the spirit of the SmileCard mascots (a simple drawing, not the real artwork;
 * swap in SmileCard's own art when it's available). Purely decorative, so screen readers skip it.
 */
export default function CardBuddy({ color = "#7b4bc4", face = "smile", size = 120, tilt = 0, className = "" }) {
  const ink = "#1f1a2e";
  return (
    <svg
      className={`card-buddy ${className}`}
      width={size}
      height={size * 1.3}
      viewBox="0 0 100 130"
      style={{ transform: `rotate(${tilt}deg)` }}
      aria-hidden="true"
      focusable="false"
    >
      <rect x="6" y="6" width="88" height="118" rx="13" fill="#ffffff" stroke={color} strokeWidth="9" />
      {face === "happy" ? (
        <>
          <path d="M28 50 q8 -10 16 0" stroke={ink} strokeWidth="4.5" fill="none" strokeLinecap="round" />
          <path d="M56 50 q8 -10 16 0" stroke={ink} strokeWidth="4.5" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="36" cy="47" r="8" fill={ink} />
          <circle cx="38.8" cy="44.2" r="2.6" fill="#ffffff" />
          <circle cx="64" cy="47" r="8" fill={ink} />
          <circle cx="66.8" cy="44.2" r="2.6" fill="#ffffff" />
        </>
      )}
      <path d="M42 63 q8 6 16 0" stroke={ink} strokeWidth="3.8" fill="none" strokeLinecap="round" />
      <ellipse cx="24" cy="60" rx="7" ry="4" fill="#f4a6c3" opacity="0.85" />
      <ellipse cx="76" cy="60" rx="7" ry="4" fill="#f4a6c3" opacity="0.85" />
      <path
        d="M50 105 C29 90 31 76 41 76 C46 76 49 80 50 83 C51 80 54 76 59 76 C69 76 71 90 50 105 Z"
        fill="none"
        stroke={color}
        strokeWidth="4.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}
