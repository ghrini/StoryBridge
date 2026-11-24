/** SmileCard's own logo, taken from the student's SmileCard website redesign. It is decoration, so it is
 *  hidden from screen readers. */

/** The SmileCard logo: a purple and a blue card leaning together, with "Smile" and "Card" handwritten. */
export function SmileCardLogo({ size = 56, ink = "#ffffff" }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true" focusable="false" className="smilecard-logo">
      <g transform="rotate(-14 38 52)">
        <rect x="18" y="24" width="38" height="58" rx="3" fill="#8e3fb5" />
        <rect x="21.5" y="27.5" width="31" height="51" rx="2" fill="#fff" />
        <path d="M27 40 q3 -3.5 6 0 M38 40 q3 -3.5 6 0" fill="none" stroke="#222" strokeWidth="1.6" strokeLinecap="round" />
        <ellipse cx="27.5" cy="45" rx="3" ry="1.8" fill="#f6b3cf" />
        <ellipse cx="44" cy="45" rx="3" ry="1.8" fill="#f6b3cf" />
      </g>
      <g transform="rotate(13 62 50)">
        <rect x="43" y="20" width="38" height="60" rx="3" fill="#2f6fd6" />
        <rect x="46.5" y="23.5" width="31" height="53" rx="2" fill="#fff" />
        <circle cx="55" cy="36" r="4.6" fill="#111" />
        <circle cx="69" cy="36" r="4.6" fill="#111" />
        <circle cx="56.6" cy="34.4" r="1.6" fill="#fff" />
        <circle cx="70.6" cy="34.4" r="1.6" fill="#fff" />
        <path d="M59.5 43 q2.5 2.2 5 0" fill="none" stroke="#222" strokeWidth="1.4" strokeLinecap="round" />
        <path
          d="M62 71 C49 63 50 52 56 52.5 C59.5 52.8 61.5 55.5 62 57.5 C62.5 55.5 64.5 52.8 68 52.5 C74 52 75 63 62 71 Z"
          fill="none"
          stroke="#8e3fb5"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </g>
      <text x="10" y="21" transform="rotate(-10 10 21)" fontFamily="'Patrick Hand', cursive" fontSize="17" fill={ink}>
        Smile
      </text>
      <text x="55" y="97" transform="rotate(-6 55 97)" fontFamily="'Patrick Hand', cursive" fontSize="17" fill={ink}>
        Card
      </text>
    </svg>
  );
}
