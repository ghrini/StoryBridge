import { HOSTED } from "../services/hosted.js";

/** The SmileCard website's closing band and dark footer (from the student's redesign), plus StoryBridge's
 *  privacy line. */
const FORM = "https://docs.google.com/forms/d/e/1FAIpQLScbifU4qpK1Ve_Ozm_0r_g-85fLoYGNTssn-7Y0YbRWeX8-Dg/viewform";
const page = (file) => `/smilecard/${encodeURIComponent(file)}.dc.html`;

const COLUMNS = [
  {
    title: "Explore",
    tone: "pink",
    links: [
      ["Home", page("SmileCard Home v7")],
      ["Card Gallery", page("Card Gallery")],
      ["Our Team", page("Our Team")],
      ["Testimonials", page("Testimonials")],
    ],
  },
  {
    title: "Get involved",
    tone: "blue",
    links: [
      ["Volunteer", page("Volunteer Opportunities")],
      ["Submit a card", FORM],
      ["Beneficiaries", page("Beneficiaries")],
      ["Senior Loneliness", page("Senior Loneliness Awareness")],
    ],
  },
  {
    title: "Contact",
    tone: "purple",
    links: [
      [<>Smilecardforeveryone<wbr />@gmail.com</>, "mailto:Smilecardforeveryone@gmail.com"],
      ["Facebook", "https://www.facebook.com/smilecardorg"],
      ["Instagram", "https://www.instagram.com/smilecard_/"],
    ],
  },
];

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site">
        <section className="footer-band" aria-label="SmileCard">
          <h2>
            <span className="display">Together we can bring a smile,</span>
            <span className="display-sans">one card at a time!</span>
          </h2>
          <div className="actions">
            <a className="pill pill-dark" href={page("Card Gallery")}>
              Download cards <span aria-hidden="true">↘</span>
            </a>
            <a className="pill pill-pink" href={FORM}>
              Submit a card <span aria-hidden="true">↗</span>
            </a>
          </div>
        </section>
      </div>
      <div className="footer-dark">
        <div className="footer-columns">
          <div className="footer-about">
            <span className="footer-brand">SmileCard</span>
            <p>Together we can bring a smile, one card at a time!</p>
            <p className="footer-note">
              StoryBridge is a SmileCard project. Its recordings, stories, and pictures stay on{" "}
              {HOSTED ? "the volunteer\u2019s" : "this"} computer.
            </p>
          </div>
          {COLUMNS.map(({ title, tone, links }) => (
            <nav key={title} aria-label={title}>
              <p className={`footer-title footer-title-${tone}`}>{title}</p>
              <ul>
                {links.map(([label, href]) => (
                  <li key={href}>
                    <a href={href}>{label}</a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <p className="footer-end">
          <span>© 2026 by SmileCard.org</span>
          <span>Made with love by student volunteers</span>
        </p>
      </div>
    </footer>
  );
}
