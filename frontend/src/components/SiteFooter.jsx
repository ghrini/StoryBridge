/** The SmileCard website's footer (from the student's redesign), plus StoryBridge's privacy line. */
const FORM = "https://docs.google.com/forms/d/e/1FAIpQLScbifU4qpK1Ve_Ozm_0r_g-85fLoYGNTssn-7Y0YbRWeX8-Dg/viewform";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <section className="footer-band" aria-label="SmileCard">
        <h2>
          <span className="display">Together we can bring a smile,</span>
          <span className="display-sans">one card at a time!</span>
        </h2>
        <div className="actions">
          <a className="pill pill-dark" href={`/smilecard/${encodeURIComponent("Card Gallery")}.dc.html`}>
            Download cards <span aria-hidden="true">↘</span>
          </a>
          <a className="pill pill-pink" href={FORM}>
            Submit a card <span aria-hidden="true">↗</span>
          </a>
        </div>
      </section>
      <div className="footer-row">
        <span className="footer-brand">SmileCard</span>
        <a href="mailto:Smilecardforeveryone@gmail.com">Smilecardforeveryone@gmail.com</a>
        <a href="https://www.facebook.com/smilecardorg">Facebook</a>
        <a href="https://www.instagram.com/smilecard_/">Instagram</a>
        <span className="footer-copy">© 2024 by SmileCard.org</span>
      </div>
      <p className="footer-note">
        StoryBridge is a SmileCard project. Its recordings, stories, and pictures stay on this computer.
      </p>
    </footer>
  );
}
