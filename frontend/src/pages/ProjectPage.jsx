import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import BookDetails from "../components/BookDetails.jsx";
import PictureBox from "../components/PictureBox.jsx";
import SentenceReview from "../components/SentenceReview.jsx";
import SharePanel from "../components/SharePanel.jsx";
import StoryChat from "../components/StoryChat.jsx";
import {
  audioUrl,
  confirmStory,
  deleteProject,
  draftStory,
  getAiHelper,
  getProject,
  photoUrl,
  removeCoverPhoto,
  removePagePhoto,
  reviseStory,
  transcribe,
  updateBookDetails,
  updateSentence,
  uploadAudio,
  uploadCoverPhoto,
  uploadPagePhoto,
} from "../services/api.js";
import { KIND_LABELS, bookTitle, countNeedingReview, formatTime, sourceSpan } from "../services/format.js";

export default function ProjectPage({ projectId, config, notify, fail, onClose, onChanged }) {
  const [project, setProject] = useState(null);
  const [version, setVersion] = useState(0); // changes whenever the project changes, to refresh the book preview
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState(null);
  const [helper, setHelper] = useState(null); // can "Ask for changes" be used for this story?
  const audioRef = useRef(null);
  const heading = useRef(null);

  const showProject = useCallback(
    (loaded) => {
      setProject(loaded);
      setVersion((v) => v + 1);
      onChanged?.(); // keep "Your stories" up to date (title, pages)
    },
    [onChanged],
  );

  useEffect(() => {
    getProject(projectId).then(showProject).catch(fail);
    getAiHelper(projectId)
      .then(setHelper)
      .catch(() => setHelper(null));
  }, [projectId, showProject, fail]);

  // Once the story has loaded, move focus (and the view) to its title.
  const focused = useRef(false);
  useEffect(() => {
    if (project && !focused.current) {
      focused.current = true;
      heading.current?.focus();
    }
  }, [project]);

  async function run(message, action) {
    setBusy(true);
    if (message) notify(message);
    try {
      return await action();
    } catch (error) {
      fail(error);
      return null;
    } finally {
      setBusy(false);
    }
  }

  /** Run a change that returns the updated project. */
  async function act(message, action, done = "Saved.") {
    const updated = await run(message, action);
    if (updated) {
      showProject(updated);
      notify(done);
    }
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      fail(new Error("Choose an audio file first."));
      return;
    }
    await act("Uploading and preparing the recording…", () => uploadAudio(projectId, file), "The recording is ready.");
  }

  async function handleMake() {
    if (
      project.chapters.length > 0 &&
      !window.confirm("Make the storybook again? The whole story is rewritten from the recording, so changes you asked for or made by hand are lost.")
    ) {
      return;
    }
    if (project.transcript.length === 0) {
      const heard = await run("Step 1 of 2: turning the recording into text on this computer. This can take a minute or two…", () =>
        transcribe(projectId),
      );
      if (!heard) return;
      showProject(heard);
    }
    const message = config?.ai_model
      ? "Step 2 of 2: writing the storybook pages with AI. This can take up to a minute…"
      : "Making the storybook pages…";
    const made = await run(message, () => draftStory(projectId));
    if (made) {
      showProject(made);
      notify(`Your storybook has ${made.chapters.length} pages. Read it in step 04.`);
    }
  }

  /** "Ask for changes": resolves to { reply, changed_pages } or { error }. */
  async function handleAsk(request) {
    setBusy(true);
    notify("Changing the story… this can take up to a minute.");
    try {
      const result = await reviseStory(projectId, request);
      showProject(result.project);
      notify(result.changed_pages.length ? "The story was changed. Read the parts marked “changed”." : "Nothing in the book changed.");
      return result;
    } catch (error) {
      notify("Nothing was changed.");
      return { error: error.message };
    } finally {
      setBusy(false);
    }
  }

  /** Take out, put back, or rewrite one sentence by hand. Resolves to true if it was saved. */
  async function handleSentence(sentenceId, changes) {
    const updated = await run("Saving…", () => updateSentence(projectId, sentenceId, changes));
    if (!updated) return false;
    showProject(updated);
    notify("Saved.");
    return true;
  }

  async function handleDelete() {
    const name = project.family_name || project.storyteller_name || "this story";
    if (!window.confirm(`Delete ${name}? This permanently removes the recording, the story, the pictures, and the voice clips.`)) {
      return;
    }
    const done = await run("Deleting…", async () => {
      await deleteProject(projectId);
      return true;
    });
    if (done) {
      notify("Deleted. The recording, story, pictures, and clips are gone from this computer.");
      onClose();
    }
  }

  function playFrom(seconds) {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = seconds;
    audio.play().catch(() => {});
  }

  if (!project) return <p>Loading…</p>;

  const consent = project.consent;
  const canRecord =
    project.recording_kind !== "storyteller" ||
    Boolean(consent && !consent.withdrawn && consent.agreed_recording && consent.agreed_local_transcription);
  const needsReview = countNeedingReview(project.chapters);
  const detailsMissing = !project.family_name || !project.pronouns;
  const hasBook = project.chapters.length > 0;
  // after the story was confirmed, mark what a later change added, so only that needs reading again
  const showChanges = needsReview > 0 && project.chapters.some((page) => page.sentences.some((s) => s.status === "approved"));
  const name = project.family_name || "the storyteller";
  const theirs = { "she/her": "her", "he/him": "his" }[project.pronouns] || "their";

  return (
    <>
      <div className="workspace-head">
        <div>
          <p className="eyebrow">The story · {KIND_LABELS[project.recording_kind]}</p>
          <h2 ref={heading} tabIndex={-1} className="workspace-title">
            <span className="display">{hasBook ? bookTitle(project) : project.family_name || project.storyteller_name || "A new story"}</span>
          </h2>
        </div>
        <button type="button" className="secondary" onClick={onClose}>
          Close this story
        </button>
      </div>
      {config && <p className="note">{config.review_notice}</p>}

      <section aria-labelledby="step-audio" className="step-card">
        <p className="step-label">01 — The recording</p>
        <h3 id="step-audio">Add the recording</h3>
        {project.audio_file ? (
          <>
            <p>Recording ready, {formatTime(project.duration_seconds)} long.</p>
            <div className="player">
              <audio ref={audioRef} controls preload="metadata" src={audioUrl(projectId)} aria-label="The recording" />
            </div>
          </>
        ) : canRecord ? (
          <form onSubmit={handleUpload} className="stack">
            <div className="field">
              <label htmlFor="audio-file">Choose the recording (WAV, MP3, M4A, WebM, OGG, or FLAC)</label>
              <input
                id="audio-file"
                type="file"
                accept="audio/*,.m4a,.webm,.opus,.flac,.mp4"
                onChange={(event) => setFile(event.target.files[0] ?? null)}
              />
            </div>
            <button type="submit" disabled={busy}>
              Upload recording
            </button>
          </form>
        ) : (
          <p className="card">
            <span aria-hidden="true">⛔ </span>This story has no consent to record, so audio cannot be added.
          </p>
        )}
      </section>

      {project.audio_file && (
        <section aria-labelledby="step-details" className="step-card">
          <p className="step-label">02 — About the book</p>
          <h3 id="step-details">Who is the story about?</h3>
          <BookDetails
            key={`${project.family_name}|${project.pronouns}|${project.book_title}|${project.suggested_title}`}
            project={project}
            busy={busy}
            onSave={(details) => act("Saving…", () => updateBookDetails(projectId, details))}
          />
        </section>
      )}

      {project.audio_file && (
        <section aria-labelledby="step-make" className="step-card">
          <p className="step-label">03 — Make the storybook</p>
          <h3 id="step-make">Turn it into a picture book</h3>
          <p>
            StoryBridge turns the recording into text on this computer, then writes it as picture-book pages about{" "}
            {project.family_name || "the storyteller"}. Every sentence stays linked to the part of the recording it
            came from.
          </p>
          <button type="button" onClick={handleMake} disabled={busy || detailsMissing} aria-describedby="make-hint">
            {hasBook ? "Make the storybook again" : "Make the storybook"}
          </button>
          <p id="make-hint">
            {detailsMissing ? "First fill in step 02: the name the family uses and pronouns." : ""}
          </p>
          {project.drafted_by && <p>Written by: {project.drafted_by}</p>}
          {project.warnings.map((warning) => (
            <p key={`${warning.code}-${warning.message}`} className="card" role="note">
              <span aria-hidden="true">⚠ </span>
              {warning.message}
            </p>
          ))}
        </section>
      )}

      {hasBook && (
        <section aria-labelledby="step-pages" className="step-card">
          <p className="step-label">04 — Read the story</p>
          <h3 id="step-pages">Read it together, ask for changes, add pictures</h3>
          <p>
            Read each page with {name} or {theirs} family. If something isn&rsquo;t right, or you&rsquo;d like it told
            differently, just say so in <strong>Ask for changes</strong>. Add a picture to any page.
          </p>

          <div className="review-layout">
            <div className="review-pages">
              <div className="page-card">
                <h4>Cover: {bookTitle(project)}</h4>
                <PictureBox
                  key={`cover-${project.cover_photo}`}
                  label="Cover picture"
                  imageUrl={project.cover_photo && photoUrl(projectId, project.cover_photo)}
                  onUpload={(picked) => act("Adding the picture…", () => uploadCoverPhoto(projectId, picked))}
                  onRemove={() => act("Removing the picture…", () => removeCoverPhoto(projectId))}
                  busy={busy}
                />
              </div>

              {project.chapters.map((page, index) => {
                const inBook = page.sentences.filter((sentence) => sentence.status !== "removed");
                return (
                  <div key={page.id} className="page-card">
                    <h4>Page {index + 2}</h4>
                    <PictureBox
                      key={`${page.id}-${page.photo_file}`}
                      label={`Picture for page ${index + 2}`}
                      imageUrl={page.photo_file && photoUrl(projectId, page.photo_file)}
                      hint={page.photo_idea}
                      onUpload={(picked) => act("Adding the picture…", () => uploadPagePhoto(projectId, page.id, picked))}
                      onRemove={() => act("Removing the picture…", () => removePagePhoto(projectId, page.id))}
                      busy={busy}
                    />
                    <div className="page-words">
                      {inBook.length > 0 ? (
                        <p className="page-text">
                          {inBook.map((sentence, position) => (
                            <Fragment key={sentence.id}>
                              {position > 0 && " "}
                              {showChanges && sentence.status === "flagged" ? (
                                <mark className="changed">
                                  {sentence.text}
                                  <span className="changed-tag">changed</span>
                                </mark>
                              ) : (
                                sentence.text
                              )}
                            </Fragment>
                          ))}
                        </p>
                      ) : (
                        <p className="page-text page-text-empty">No words on this page, so it is left out of the book.</p>
                      )}
                      <details className="fix-by-hand">
                        <summary>Fix this page by hand</summary>
                        <ol className="sentences">
                          {page.sentences.map((sentence) => (
                            <SentenceReview
                              key={`${sentence.id}-${sentence.text}-${sentence.status}`}
                              sentence={sentence}
                              span={sourceSpan(project.transcript, sentence.source_segment_ids)}
                              onPlaySource={playFrom}
                              onUpdate={handleSentence}
                              busy={busy}
                            />
                          ))}
                        </ol>
                      </details>
                    </div>
                  </div>
                );
              })}
            </div>

            <aside className="review-chat" aria-label="Ask for changes">
              <StoryChat name={project.family_name} helper={helper} busy={busy} onAsk={handleAsk} />
            </aside>

            <div className={`confirm-box${needsReview === 0 ? " confirm-done" : ""}`}>
              {needsReview === 0 ? (
                <p role="status">
                  <span aria-hidden="true">✓ </span>
                  <strong>You confirmed the story.</strong> Printing and sharing are open in step 05. If you ask for
                  more changes, you&rsquo;ll read just those and confirm again.
                </p>
              ) : (
                <>
                  <p role="status">
                    <strong>
                      {showChanges
                        ? `Read the ${needsReview} changed ${needsReview === 1 ? "sentence" : "sentences"} (marked “changed”).`
                        : "Finished reading?"}
                    </strong>{" "}
                    When {name} or {theirs} family agree the story is right, confirm it to unlock printing and sharing.
                  </p>
                  <button
                    type="button"
                    onClick={() =>
                      act("Saving…", () => confirmStory(projectId), "Confirmed. You can print and share the book in step 05.")
                    }
                    disabled={busy}
                  >
                    <span aria-hidden="true">✓ </span>The story is right
                  </button>
                </>
              )}
            </div>
          </div>
        </section>
      )}

      {hasBook && (
        <section aria-labelledby="step-share" className="step-card">
          <p className="step-label">05 — Your book</p>
          <h3 id="step-share">Flip through, print, and share</h3>
          <SharePanel
            project={project}
            config={config}
            ready={needsReview === 0}
            notReadyReason="Read the story in step 04, then press “The story is right”."
            version={version}
            busy={busy}
            run={run}
            notify={notify}
          />
        </section>
      )}

      <section aria-labelledby="step-delete" className="danger-zone">
        <h3 id="step-delete">Withdraw and delete</h3>
        <p>If the storyteller changes their mind, delete everything for this story.</p>
        <button type="button" className="danger" onClick={handleDelete} disabled={busy}>
          <span aria-hidden="true">⚠ </span>Delete this story and its recording
        </button>
      </section>
    </>
  );
}
