import CardBuddy from "./CardBuddy.jsx";

/** A small open book with picture boxes, drawn for the "How it works" section. */
function BookSketch() {
  return (
    <svg viewBox="0 0 320 200" className="book-sketch" aria-hidden="true" focusable="false">
      <rect x="0" y="0" width="320" height="200" rx="26" fill="#efe8f8" />
      <path d="M40 46 L158 38 L158 168 L40 176 Z" fill="#ffffff" stroke="#d9cfe9" strokeWidth="2" />
      <path d="M162 38 L280 46 L280 176 L162 168 Z" fill="#ffffff" stroke="#d9cfe9" strokeWidth="2" />
      <rect x="54" y="56" width="90" height="58" rx="8" fill="#f2eefa" stroke="#b9a9d6" strokeDasharray="5 4" />
      <rect x="176" y="56" width="90" height="58" rx="8" fill="#f2eefa" stroke="#b9a9d6" strokeDasharray="5 4" />
      {[126, 138, 150].map((y) => (
        <g key={y}>
          <line x1="60" y1={y} x2={y === 150 ? 118 : 138} y2={y} stroke="#cfc4e3" strokeWidth="4" strokeLinecap="round" />
          <line x1="182" y1={y} x2={y === 150 ? 236 : 260} y2={y} stroke="#cfc4e3" strokeWidth="4" strokeLinecap="round" />
        </g>
      ))}
    </svg>
  );
}

/** The white "How it works" card, laid out like the SmileCard "Why we started" section. */
export default function HowItWorks() {
  return (
    <section className="section-card" id="how" aria-labelledby="how-title">
      <div className="why-head">
        <div>
          <p className="eyebrow">How it works</p>
          <h2 id="how-title">
            <span className="display">A recording is all it takes</span>
            <span className="display-sans">to keep a memory.</span>
          </h2>
        </div>
        <div className="why-art">
          <BookSketch />
          <CardBuddy className="why-buddy-left" color="#c2318f" face="smile" size={58} tilt={-8} />
          <CardBuddy className="why-buddy-right" color="#3a6fe0" face="happy" size={58} tilt={7} />
        </div>
      </div>

      <ol className="why-steps">
        <li>
          <p className="step-label">01 — Listen</p>
          <h3>Record a memory</h3>
          <p>
            With their permission, record a grandparent telling a story, like a typical day in high school. The
            recording stays on this computer and is turned into text right here.
          </p>
        </li>
        <li>
          <p className="step-label">02 — Write</p>
          <h3>A picture book, not a transcript</h3>
          <p>
            AI turns what was said into short picture-book pages about them, and is told never to add anything they
            didn&rsquo;t say. Every sentence links back to the moment in the recording it came from.
          </p>
        </li>
        <li>
          <p className="step-label">03 — Share</p>
          <h3>Check it, then share it</h3>
          <p>
            You check every sentence, add photos or drawings, flip through the book, then print it or send it to
            family.
          </p>
        </li>
      </ol>
    </section>
  );
}
