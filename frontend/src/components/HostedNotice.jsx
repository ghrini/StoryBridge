import { ASK_US } from "../services/hosted.js";

/** On the public website, shown where the story tools are in the app on a volunteer's computer. */
export default function HostedNotice() {
  return (
    <section className="panels" aria-label="About making a book">
      <div className="panel panel-lilac" id="ask">
        <p className="eyebrow eyebrow-pink">For families</p>
        <h2 className="panel-title">
          <span className="display">A book for</span> <span className="display">someone you love.</span>
        </h2>
        <p>
          StoryBridge runs on a SmileCard volunteer&rsquo;s own computer, so stories can&rsquo;t be started on this
          website. If you&rsquo;d like to know more, write to us.
        </p>
        <p className="actions">
          <a className="pill pill-pink" href={ASK_US}>
            Write to us <span aria-hidden="true">↗</span>
          </a>
        </p>
      </div>

      <div className="panel panel-blue">
        <p className="eyebrow eyebrow-blue">Privacy</p>
        <h2 className="panel-title">
          <span className="display">Their story</span> <span className="display">stays theirs.</span>
        </h2>
        <p>
          The voice recording never leaves the volunteer&rsquo;s computer. Nothing is recorded without the
          storyteller&rsquo;s permission, and nothing is shared until the family says it is right.
        </p>
        <p className="actions">
          <a className="pill pill-dark" href="/smilecard/StoryBridge.dc.html">
            About StoryBridge <span aria-hidden="true">↗</span>
          </a>
        </p>
      </div>
    </section>
  );
}
