/** Thin wrappers around the StoryBridge server. Every function throws an Error with a readable message. */
import { filenameFromDisposition } from "./format.js";

async function request(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("Could not reach the StoryBridge server. Is it still running?");
  }
  if (!response.ok) {
    let message = `Something went wrong (error ${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).join(" ");
    } catch {
      /* keep the generic message */
    }
    throw new Error(message);
  }
  return response;
}

async function json(path, options) {
  return (await request(path, options)).json();
}

const jsonBody = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function fileForm(file) {
  const form = new FormData();
  form.append("file", file);
  return form;
}

const base = (id) => `/api/projects/${id}`;

// --- projects -----------------------------------------------------------------------------------
export const getConfig = () => json("/api/config");
export const listProjects = () => json("/api/projects");
export const getProject = (id) => json(base(id));
export const createProject = (body) => json("/api/projects", jsonBody("POST", body));
export const deleteProject = (id) => json(base(id), { method: "DELETE" });
/** { family_name, pronouns, book_title } — only the keys given are changed. */
export const updateBookDetails = (id, details) => json(base(id), jsonBody("PATCH", details));

// --- recording, text, and the story -------------------------------------------------------------
export const audioUrl = (id) => `${base(id)}/audio`;
export const uploadAudio = (id, file) => json(`${base(id)}/audio`, { method: "POST", body: fileForm(file) });
export const transcribe = (id) => json(`${base(id)}/transcribe`, { method: "POST" });
/** Make the storybook pages from the transcript. */
export const draftStory = (id) => json(`${base(id)}/draft`, { method: "POST" });
/** A change to one sentence by hand: { status } and/or { text }. */
export const updateSentence = (id, sentenceId, changes) =>
  json(`${base(id)}/sentences/${sentenceId}`, jsonBody("PATCH", changes));
/** Whether "Ask for changes" can be used for this story: { available, reason }. */
export const getAiHelper = (id) => json(`${base(id)}/ai-helper`);
/** Change the story the way the reviewer asks. Resolves to { project, reply, changed_pages }. */
export const reviseStory = (id, request) => json(`${base(id)}/revise`, jsonBody("POST", { request }));
/** A person read the whole story and says it is right (unlocks printing and sharing). */
export const confirmStory = (id) => json(`${base(id)}/confirm`, { method: "POST" });

// --- pictures -----------------------------------------------------------------------------------
export const photoUrl = (id, relative) => `${base(id)}/${relative}`;
export const uploadCoverPhoto = (id, file) => json(`${base(id)}/cover-photo`, { method: "PUT", body: fileForm(file) });
export const removeCoverPhoto = (id) => json(`${base(id)}/cover-photo`, { method: "DELETE" });
export const uploadPagePhoto = (id, pageId, file) =>
  json(`${base(id)}/pages/${pageId}/photo`, { method: "PUT", body: fileForm(file) });
export const removePagePhoto = (id, pageId) => json(`${base(id)}/pages/${pageId}/photo`, { method: "DELETE" });

// --- the book -----------------------------------------------------------------------------------
/** Pictures of every page for the page flipper: { title, reviewed, pages: [url, ...] }. */
export const getBookPreview = (id) => json(`${base(id)}/book-preview`);
/** edition: "print" (bleed + voice QR codes) or "family" (for sending to family). */
export const bookUrl = (id, edition, inline = false) => `${base(id)}/book.pdf?edition=${edition}${inline ? "&inline=true" : ""}`;

async function fetchFile(path, fallbackName, type) {
  const response = await request(path);
  const name = filenameFromDisposition(response.headers.get("Content-Disposition"), fallbackName);
  return new File([await response.blob()], name, { type });
}

export const fetchBook = (id, edition) => fetchFile(bookUrl(id, edition), `storybook-${edition}.pdf`, "application/pdf");
export const fetchPageImages = (id) => fetchFile(`${base(id)}/book-pages.zip`, "storybook-pages.zip", "application/zip");

/** Save a file through the browser's normal download. */
export function saveFile(file) {
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

/**
 * Open the device's share menu (WhatsApp appears there when it is installed). If this browser cannot share
 * files, save the file instead so it can be attached by hand.
 * @returns {Promise<"shared"|"cancelled"|"downloaded">}
 */
export async function shareOrSave(file, title) {
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title, text: `${title} — a StoryBridge storybook` });
      return "shared";
    } catch (error) {
      if (error.name === "AbortError") return "cancelled";
      // any other problem (for example the browser refused): fall back to saving the file
    }
  }
  saveFile(file);
  return "downloaded";
}
