import CardBuddy from "./CardBuddy.jsx";

const STEPS = [
  ["01", "Record"],
  ["02", "Write"],
  ["03", "Check"],
  ["04", "Share"],
];

/** The top of the page: a dusk-coloured banner with the menu, the headline, and the four steps. */
export default function Hero() {
  return (
    <header className="hero">
      <nav className="nav" aria-label="Main">
        <a className="brand" href="#main">
          <CardBuddy size={30} color="#8a4fd0" face="happy" tilt={-8} />
          <span className="brand-name">StoryBridge</span>
          <span className="brand-by">by SmileCard</span>
        </a>
        <ul className="nav-links">
          <li>
            <a href="#how">How it works</a>
          </li>
          <li>
            <a href="#your-stories">Your stories</a>
          </li>
          <li>
            <a href="#start">Start a story</a>
          </li>
        </ul>
      </nav>

      <div className="hero-grid">
        <div className="hero-copy">
          <p className="eyebrow eyebrow-light">A SmileCard project · Stories from grandparents</p>
          <h1>
            <span className="display">Their stories,</span>
            <span className="display-sans">kept in a picture book.</span>
          </h1>
          <p className="hero-lead">
            Record a grandparent telling a memory. StoryBridge turns it into a simple picture book that you check,
            fill with pictures, print, and share with family.
          </p>
          <div className="hero-actions">
            <a className="pill pill-white" href="#start">
              Start a story <span aria-hidden="true">↘</span>
            </a>
            <a className="pill pill-ghost" href="#your-stories">
              Your stories <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <span className="hero-word hero-word-top">Story</span>
          <CardBuddy className="buddy-back" color="#8a4fd0" face="happy" size={150} tilt={-12} />
          <CardBuddy className="buddy-front" color="#3a6fe0" face="smile" size={168} tilt={9} />
          <span className="hero-word hero-word-bottom">Book</span>
        </div>
      </div>

      <ol className="hero-steps">
        {STEPS.map(([number, label]) => (
          <li key={number}>
            <span className="hero-step-number">{number}</span>
            <span className="hero-step-label">{label}</span>
          </li>
        ))}
      </ol>
    </header>
  );
}
