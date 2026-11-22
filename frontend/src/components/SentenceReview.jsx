import { useState } from "react";
import { formatTime, shortText } from "../services/format.js";

/** One sentence in a page's "Fix this page by hand" list: hear where it came from, rewrite it, or take it out. */
export default function SentenceReview({ sentence, span, onPlaySource, onUpdate, busy }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(sentence.text);
  const removed = sentence.status === "removed";
  const context = <span className="visually-hidden"> sentence: {shortText(sentence.text)}</span>;

  async function save() {
    // keep the editor open (and the typing) if the save failed
    if (await onUpdate(sentence.id, { text: draft })) setEditing(false);
  }

  return (
    <li className={`sentence${removed ? " sentence-removed" : ""}`}>
      {removed && (
        <p className="sentence-status">
          <span aria-hidden="true">✕ </span>Taken out of the book
        </p>
      )}

      {editing ? (
        <div className="field">
          <label htmlFor={`edit-${sentence.id}`}>Edit this sentence</label>
          <textarea id={`edit-${sentence.id}`} rows={3} value={draft} onChange={(event) => setDraft(event.target.value)} />
          <div className="actions">
            <button type="button" onClick={save} disabled={busy}>
              Save sentence
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setDraft(sentence.text);
                setEditing(false);
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <p className="sentence-text">{sentence.text}</p>
      )}

      <p className="segment-time">
        {span
          ? `From the recording at ${formatTime(span.start)}–${formatTime(span.end)}`
          : "From a message you sent (not in the recording)"}
      </p>

      {!editing && (
        <div className="actions">
          {span && (
            <button type="button" className="secondary" onClick={() => onPlaySource(span.start)}>
              Play source{context}
            </button>
          )}
          {removed ? (
            <button type="button" className="secondary" onClick={() => onUpdate(sentence.id, { status: "flagged" })} disabled={busy}>
              Put back{context}
            </button>
          ) : (
            <>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setDraft(sentence.text);
                  setEditing(true);
                }}
              >
                Edit{context}
              </button>
              <button type="button" className="secondary" onClick={() => onUpdate(sentence.id, { status: "removed" })} disabled={busy}>
                Take out{context}
              </button>
            </>
          )}
        </div>
      )}
    </li>
  );
}
