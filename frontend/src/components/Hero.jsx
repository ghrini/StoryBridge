import { SmileCardLogo } from "./SmileCardArt.jsx";

/** The redesigned SmileCard website, served by this same computer at /smilecard/. */
const SITE = "/smilecard/";
const page = (file) => `${SITE}${encodeURIComponent(file)}.dc.html`;

const MENU = [
  { label: "Home", href: page("SmileCard Home v7") },
  { label: "Card Gallery", href: page("Card Gallery") },
  { label: "Volunteer", href: page("Volunteer Opportunities") },
  { label: "Our Team", href: page("Our Team") },
  { label: "StoryBridge", href: "#main", current: true },
];

const MORE = [
  ["Beneficiaries", page("Beneficiaries")],
  ["Volunteers", page("Volunteers")],
  ["Senior Loneliness Awareness", page("Senior Loneliness Awareness")],
  ["Testimonials", page("Testimonials")],
];

const STEPS = [
  ["01", "Record"],
  ["02", "Write"],
  ["03", "Read together"],
  ["04", "Share"],
];

/** The top of the page, in the SmileCard website's style: the hills drawing across the whole window, the
 *  SmileCard menu (with StoryBridge as one of its pages), the headline, and the four steps. */
export default function Hero() {
  return (
    <header className="hero">
      <div className="hero-bar">
        <a className="brand" href={page("SmileCard Home v7")}>
          <SmileCardLogo size={56} />
          <span className="brand-name">SmileCard</span>
          <span className="visually-hidden"> home page</span>
        </a>
        <nav aria-label="SmileCard">
          <ul className="nav-links">
            {MENU.map((item) => (
              <li key={item.label}>
                <a href={item.href} aria-current={item.current ? "page" : undefined}>
                  {item.label}
                </a>
              </li>
            ))}
            <li>
              <details className="nav-more">
                <summary>More</summary>
                <ul>
                  {MORE.map(([label, href]) => (
                    <li key={label}>
                      <a href={href}>{label}</a>
                    </li>
                  ))}
                </ul>
              </details>
            </li>
          </ul>
        </nav>
      </div>

      <div className="hero-body">
        <div className="hero-copy">
          <p className="eyebrow eyebrow-light">A SmileCard project · Stories from grandparents</p>
          <h1>
            <span className="display">StoryBridge</span>
            <span className="display-sans">their stories, kept in a picture book.</span>
          </h1>
          <p className="hero-lead">
            Record a grandparent telling a memory. StoryBridge turns it into a simple picture book that you read
            together, fill with pictures, print, and share with family.
          </p>
          <div className="hero-actions">
            <a className="pill pill-white" href="#start">
              Start a story <span aria-hidden="true">↘</span>
            </a>
            <a className="pill pill-pink" href="#your-stories">
              Your stories <span aria-hidden="true">↗</span>
            </a>
          </div>
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
