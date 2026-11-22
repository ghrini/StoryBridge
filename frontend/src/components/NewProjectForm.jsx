import { useState } from "react";
import { KIND_LABELS } from "../services/format.js";

const PERMISSIONS = [
  { key: "agreed_recording", label: "The storyteller agrees to be recorded." },
  {
    key: "agreed_local_transcription",
    label: "The storyteller agrees the recording may be turned into text on this computer (nothing is sent over the internet).",
  },
  { key: "agreed_book", label: "The storyteller agrees a short book may be made from their own words." },
  { key: "agreed_audio_qr", label: "The storyteller agrees the book's QR codes may play their voice." },
  {
    key: "agreed_video",
    label: "The storyteller agrees their voice, name, photo, or quotes may be used in the demo video.",
  },
  {
    key: "agreed_external_ai",
    label:
      "The storyteller agrees their words, as written text and never as audio, may be sent to Google's Gemini AI service to help draft the story and make the changes the family asks for. On free Google accounts, Google may keep and use what it receives, and people there may read it. Leave this unchecked unless they specifically agree.",
  },
];

const today = () => new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD in local time

export default function NewProjectForm({ onCreate, busy }) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState("storyteller");
  const [permissions, setPermissions] = useState({});
  const [facility, setFacility] = useState("not_applicable");
  const [agreedOn, setAgreedOn] = useState(today());
  const [notes, setNotes] = useState("");
  const [problem, setProblem] = useState("");

  const needsConsent = kind === "storyteller";

  function submit(event) {
    event.preventDefault();
    if (needsConsent && !(permissions.agreed_recording && permissions.agreed_local_transcription)) {
      setProblem(
        "Without agreement to be recorded and to turning the recording into text on this computer, this story cannot be recorded for StoryBridge.",
      );
      return;
    }
    setProblem("");
    const consent = needsConsent
      ? {
          agreed_on: agreedOn,
          ...Object.fromEntries(PERMISSIONS.map(({ key }) => [key, Boolean(permissions[key])])),
          facility_permission: facility,
          notes: notes.trim(),
        }
      : null;
    onCreate({ storyteller_name: name.trim() || null, recording_kind: kind, consent });
  }

  return (
    <form onSubmit={submit} className="stack">
      <div className="card">
        <h3>How StoryBridge treats a recording</h3>
        <ul>
          <li>The recording itself stays on this computer. The audio is never uploaded to the internet.</li>
          <li>It is turned into text on this computer too.</li>
          <li>
            Only if the storyteller specifically agrees, the written text (never the audio) may be sent to
            Google&rsquo;s Gemini AI service to help draft the storybook. Otherwise nothing is sent anywhere.
          </li>
          <li>
            While this program is running, anyone on the same Wi-Fi who scans a QR code in the printed book can play
            that page&rsquo;s voice clip. Nothing else is shared.
          </li>
          <li>
            The storyteller can stop, skip a question, or change their mind at any time. Withdrawing deletes the
            recording, the text, and the audio clips.
          </li>
          <li>
            Never put health details, addresses, money details, or other people&rsquo;s private information in the book.
          </li>
        </ul>
      </div>

      <div className="field">
        <label htmlFor="storyteller-name">Storyteller&rsquo;s name (optional; a first name is fine)</label>
        <input id="storyteller-name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
      </div>

      <div className="field">
        <label htmlFor="recording-kind">What kind of recording is this?</label>
        <select id="recording-kind" value={kind} onChange={(e) => setKind(e.target.value)}>
          {Object.entries(KIND_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {needsConsent ? (
        <fieldset>
          <legend>What did the storyteller agree to? (Use the consent form first, then record it here.)</legend>
          {PERMISSIONS.map(({ key, label }) => (
            <label key={key} className="check">
              <input
                type="checkbox"
                checked={Boolean(permissions[key])}
                onChange={(e) => setPermissions({ ...permissions, [key]: e.target.checked })}
              />
              <span>{label}</span>
            </label>
          ))}
          <div className="field">
            <label htmlFor="facility">Care facility</label>
            <select id="facility" value={facility} onChange={(e) => setFacility(e.target.value)}>
              <option value="not_applicable">Not recorded in a care facility</option>
              <option value="granted">Recorded in a care facility, and the facility gave permission</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="agreed-on">Date they agreed</label>
            <input id="agreed-on" type="date" value={agreedOn} onChange={(e) => setAgreedOn(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="consent-notes">Notes (optional)</label>
            <input id="consent-notes" type="text" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </fieldset>
      ) : (
        <p className="card">
          This is not a real person&rsquo;s story, so no consent is needed. The book will be clearly labeled as a demo.
        </p>
      )}

      {problem && (
        <p role="alert" className="status status-error">
          <span aria-hidden="true">⚠ </span>Problem: {problem}
        </p>
      )}
      <button type="submit" className="pill-teal" disabled={busy}>
        Create story <span aria-hidden="true">↘</span>
      </button>
    </form>
  );
}
