/**
 * SmileCard's own artwork, taken from the student's SmileCard website redesign: the two-card logo and the
 * smiling-card friends (a pink "young" card with a bow, and a blue "senior" card with glasses).
 * All of it is decoration, so it is hidden from screen readers.
 */

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

/** One smiling-card friend. young = the pink card with a bow; otherwise the blue card with glasses. */
export function CardFriend({ young = false, size = 58, happy = true }) {
  const color = young ? "#c0399f" : "#2f6fd6";
  return (
    <svg
      viewBox="0 0 46 62"
      width={size}
      height={Math.round((size * 62) / 46)}
      aria-hidden="true"
      focusable="false"
      style={{ display: "block", overflow: "visible" }}
    >
      <rect x="0" y="0" width="46" height="62" rx="5" fill={color} />
      <rect x="3.5" y="3.5" width="39" height="55" rx="3" fill="#fff" />
      {young ? (
        <>
          <path d="M3.5 16 C6 6 14 4 23 6 C32 4 40 6 42.5 16 L42.5 6.5 Q42.5 3.5 39.5 3.5 L6.5 3.5 Q3.5 3.5 3.5 6.5 Z" fill="#5a3426" />
          <path d="M33 6 l-6 -5 v10 Z M33 6 l6 -5 v10 Z" fill="#ff6fb3" />
          <circle cx="33" cy="6" r="1.8" fill="#e0479a" />
        </>
      ) : (
        [8, 15, 23, 31, 38].map((x, i) => <circle key={x} cx={x} cy={7 + (i % 2)} r="5.2" fill="#d7d6de" />)
      )}
      <ellipse cx="11" cy="32" rx="3.4" ry="2" fill="#f6b3cf" />
      <ellipse cx="35" cy="32" rx="3.4" ry="2" fill="#f6b3cf" />
      {!young && (
        <>
          <circle cx="15" cy="24" r="6" fill="rgba(200,225,255,0.25)" stroke="#6b4f9e" strokeWidth="1.4" />
          <circle cx="31" cy="24" r="6" fill="rgba(200,225,255,0.25)" stroke="#6b4f9e" strokeWidth="1.4" />
          <path d="M21 23.5 q2 -1.6 4 0" fill="none" stroke="#6b4f9e" strokeWidth="1.4" />
        </>
      )}
      {happy ? (
        <>
          <path d="M11 25 q4 -5 8 0 M27 25 q4 -5 8 0" fill="none" stroke="#222" strokeWidth="2" strokeLinecap="round" />
          <path d="M16 34 q7 9 14 0 Z" fill="#222" stroke="#222" strokeWidth="1.4" strokeLinejoin="round" />
        </>
      ) : (
        <>
          <circle cx="15" cy="24" r="3.4" fill="#111" />
          <circle cx="31" cy="24" r="3.4" fill="#111" />
          <circle cx="16.2" cy="22.7" r="1.1" fill="#fff" />
          <circle cx="32.2" cy="22.7" r="1.1" fill="#fff" />
          <path d="M18 34 q5 3.6 10 0" fill="none" stroke="#222" strokeWidth="1.8" strokeLinecap="round" />
        </>
      )}
      <path
        d="M23 54 C15 49 16 42 19.5 42.3 C21.5 42.5 22.7 44 23 45.3 C23.3 44 24.5 42.5 26.5 42.3 C30 42 31 49 23 54 Z"
        fill="none"
        stroke={color}
        strokeWidth="1.4"
      />
    </svg>
  );
}

/** The two friends side by side. With bobbing, they move gently (only in the banner, to keep scrolling
 *  smooth; the motion stops for people who ask their computer for less motion). */
export function FriendsDuo({ size = 58, className = "", bobbing = false }) {
  const bob = bobbing ? "bob " : "";
  return (
    <div className={`friends-duo ${className}`} aria-hidden="true">
      <div className={`${bob}tilt-left`}>
        <CardFriend young size={size} />
      </div>
      <div className={`${bob}tilt-right`}>
        <CardFriend size={size} />
      </div>
    </div>
  );
}

/** A friend peeking over the top edge of a coloured panel. */
export function PeekingFriend({ young = false }) {
  return (
    <div className={`peeking-friend ${young ? "peek-young" : "peek-senior"}`} aria-hidden="true">
      <CardFriend young={young} size={64} happy={false} />
    </div>
  );
}
