import BookViewer from "./BookViewer.jsx";
import { fetchBook, fetchPageImages, saveFile, shareOrSave } from "../services/api.js";
import { bookTitle, qrPointsAtThisComputerOnly } from "../services/format.js";

/** Flip through the book, then download it in each edition or share it with family. */
export default function SharePanel({ project, config, ready, notReadyReason, version, busy, run, notify }) {
  const title = bookTitle(project);
  const viewer = <BookViewer projectId={project.id} version={version} />;
  if (!ready) {
    return (
      <>
        {viewer}
        <p className="card">
          <span aria-hidden="true">🔒 </span>Printing and sharing unlock when the book is ready. {notReadyReason}
        </p>
      </>
    );
  }
  const qrForPhonesOnly = config && !qrPointsAtThisComputerOnly(config.base_url);

  async function download(message, fetcher, done) {
    const file = await run(message, fetcher);
    if (file) {
      saveFile(file);
      notify(done);
    }
  }

  async function share() {
    const file = await run("Preparing the book for family…", () => fetchBook(project.id, "family"));
    if (!file) return;
    const result = await shareOrSave(file, title);
    notify(
      result === "shared"
        ? "Shared."
        : result === "cancelled"
          ? "Sharing was cancelled."
          : "This browser can't open the share menu, so the book was downloaded instead. Attach it in WhatsApp or an email.",
    );
  }

  return (
    <>
      {viewer}

      <h4>Share with family</h4>
      <p>Opens your computer&rsquo;s share menu with the book as a PDF. WhatsApp appears there if it is installed.</p>
      <div className="actions">
        <button type="button" onClick={share} disabled={busy}>
          Share with family (WhatsApp and more)
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => download("Preparing the family edition…", () => fetchBook(project.id, "family"), "Saved the family edition. Look in your Downloads folder.")}
        >
          Download the family edition (PDF)
        </button>
      </div>

      <h4>Print it</h4>
      <p>
        The print edition is 8 × 8 inches with a 1/8 inch bleed on every side, ready for print services that accept a
        PDF.{" "}
        {qrForPhonesOnly
          ? "Its QR codes play the storyteller's voice while this computer is on the same Wi-Fi."
          : `Its QR codes point to ${config?.base_url ?? "this computer"}, which phones cannot reach; set BASE_URL to this computer's network address first.`}
      </p>
      <div className="actions">
        <button
          type="button"
          disabled={busy}
          onClick={() => download("Building the print edition…", () => fetchBook(project.id, "print"), "Saved the print edition. Look in your Downloads folder.")}
        >
          Download the print edition (PDF)
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() => download("Making a picture of every page…", () => fetchPageImages(project.id), "Saved the page pictures (ZIP). Look in your Downloads folder.")}
        >
          Download page pictures for photo-book sites (ZIP)
        </button>
      </div>
      <p>
        For photo-book sites that build books from photos: choose an 8 × 8 inch book and place each page picture as a
        full-page photo, in order.
      </p>
    </>
  );
}
