import { useEffect, useState } from "react";
import { getBookPreview } from "../services/api.js";
import { spreadLabel } from "../services/format.js";

/**
 * The book as an open book on a desk: pages turn over when you click them, press the buttons, or use the
 * arrow keys. The pictures are the real pages of the family edition.
 */
export default function BookViewer({ projectId, version }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [turned, setTurned] = useState(0); // how many leaves are turned over to the left

  useEffect(() => {
    let cancelled = false;
    setError("");
    getBookPreview(projectId)
      .then((data) => {
        if (cancelled) return;
        setPreview(data);
        setTurned((current) => Math.min(current, Math.ceil(data.pages.length / 2)));
      })
      .catch((problem) => !cancelled && setError(problem.message));
    return () => {
      cancelled = true;
    };
  }, [projectId, version]);

  if (error) {
    return (
      <p className="card">
        <span aria-hidden="true">⚠ </span>The page preview could not be made: {error}
      </p>
    );
  }
  if (!preview) return <p>Making the page preview…</p>;

  const pages = preview.pages;
  const leaves = Math.ceil(pages.length / 2);
  const canGoBack = turned > 0;
  const canGoForward = turned < leaves;
  const next = () => canGoForward && setTurned(turned + 1);
  const back = () => canGoBack && setTurned(turned - 1);
  const position = turned === 0 ? "closed-front" : turned === leaves ? "closed-back" : "open";
  const bust = `?v=${version}`;

  return (
    <div className="book-viewer">
      {!preview.reviewed && (
        <p className="card">
          <span aria-hidden="true">⚠ </span>The story isn&rsquo;t confirmed yet, so every page is stamped
          &ldquo;PREVIEW&rdquo;. The stamp goes away once you press &ldquo;The story is right&rdquo; in step 04.
        </p>
      )}
      <div
        className="book-stage"
        tabIndex={0}
        role="group"
        aria-label={`Page flipper for ${preview.title}. Use the left and right arrow keys to turn pages.`}
        onKeyDown={(event) => {
          if (event.key === "ArrowRight") {
            event.preventDefault();
            next();
          } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            back();
          }
        }}
      >
        <div className={`book ${position}`}>
          {Array.from({ length: leaves }, (_, i) => {
            const isTurned = i < turned;
            const front = pages[2 * i];
            const backPage = pages[2 * i + 1];
            return (
              <div
                key={i}
                className={isTurned ? "leaf turned" : "leaf"}
                style={{ zIndex: isTurned ? i + 1 : leaves * 2 - i }}
                onClick={() => (isTurned ? i === turned - 1 && back() : i === turned && next())}
              >
                <div className="face front">
                  <img src={front + bust} alt="" draggable="false" />
                </div>
                <div className="face back">{backPage && <img src={backPage + bust} alt="" draggable="false" />}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="book-controls">
        <button type="button" className="secondary" onClick={back} disabled={!canGoBack}>
          <span aria-hidden="true">◀ </span>Previous page
        </button>
        <p className="book-position" aria-live="polite">
          {spreadLabel(turned, pages.length)}
        </p>
        <button type="button" className="secondary" onClick={next} disabled={!canGoForward}>
          Next page<span aria-hidden="true"> ▶</span>
        </button>
      </div>
      <p className="visually-hidden">
        The page flipper is a picture preview of the book. All of the story&rsquo;s words are also in step 04.
      </p>
    </div>
  );
}
