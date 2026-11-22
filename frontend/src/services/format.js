/**
 * @typedef {{id: string, text: string, start: number, end: number}} Segment
 * @typedef {{id: string, text: string, status: string, edit_type: string, source_segment_ids: string[]}} Sentence
 * @typedef {{id: string, sentences: Sentence[]}} Page  (the server calls pages "chapters")
 */

export const KIND_LABELS = {
  storyteller: "Real storyteller",
  self_demo: "My own demo recording",
  synthetic_dev: "Computer-voice test (not a real person)",
};

/** Seconds -> "m:ss". */
export function formatTime(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/** How many new or changed sentences a person has not read and confirmed yet. */
export function countNeedingReview(/** @type {Page[]} */ pages) {
  return pages.reduce((total, page) => total + page.sentences.filter((s) => s.status === "flagged").length, 0);
}

/**
 * The stretch of recording a sentence is based on, or null if its source lines are not found.
 * @param {Segment[]} transcript
 * @param {string[]} segmentIds
 */
export function sourceSpan(transcript, segmentIds) {
  const found = transcript.filter((segment) => segmentIds.includes(segment.id));
  if (found.length === 0) return null;
  return { start: Math.min(...found.map((s) => s.start)), end: Math.max(...found.map((s) => s.end)) };
}

/** The first few words of a sentence, for screen-reader button labels. */
export function shortText(text, words = 6) {
  const parts = text.trim().split(/\s+/);
  return parts.length <= words ? text.trim() : `${parts.slice(0, words).join(" ")}…`;
}

/** The title the book will show: a person's title, else the suggestion, else "<Name>'s Story". (Matches the server.) */
export function bookTitle(project) {
  for (const title of [project.book_title, project.suggested_title]) {
    if (title && title.trim()) return title.trim();
  }
  const name = (project.family_name || project.storyteller_name || "").trim();
  if (!name) return "A Life Story";
  return name.endsWith("s") ? `${name}' Story` : `${name}'s Story`;
}

/** The file name from a Content-Disposition header, or the fallback. */
export function filenameFromDisposition(header, fallback) {
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header || "");
  return match ? decodeURIComponent(match[1]) : fallback;
}

/**
 * Words for what the page flipper is showing. `turned` = how many leaves have been turned over;
 * each leaf has two pages (front on the right, back on the left once turned).
 */
export function spreadLabel(turned, pageCount) {
  if (pageCount === 0) return "No pages";
  if (turned === 0) return `Cover (page 1 of ${pageCount})`;
  const left = 2 * turned;
  const right = left + 1;
  if (right <= pageCount) return `Pages ${left}–${right} of ${pageCount}`;
  if (left <= pageCount) return `Page ${left} of ${pageCount}, the back of the book`;
  return "The back of the book";
}

/** True if QR codes would point somewhere a phone cannot reach. */
export function qrPointsAtThisComputerOnly(baseUrl) {
  return /\/\/(localhost|127\.0\.0\.1|\[::1\])(:|\/|$)/.test(baseUrl);
}
