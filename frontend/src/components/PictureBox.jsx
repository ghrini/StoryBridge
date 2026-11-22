import { useRef, useState } from "react";

/**
 * A picture box, shaped like the one in the book. A picture can be chosen from the computer, dropped onto
 * the box, or pasted (Ctrl+V) after copying it from anywhere: Google Photos, a website, an email, a screenshot.
 */
export default function PictureBox({ label, imageUrl, hint, onUpload, onRemove, busy }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);

  function take(file) {
    if (file && file.type.startsWith("image/")) onUpload(file);
  }

  return (
    <div className="picture-box-wrap">
      <div
        className={`picture-box${dragging ? " dragging" : ""}`}
        tabIndex={0}
        role="group"
        aria-label={`${label}: ${imageUrl ? "has a picture" : "no picture yet"}. Paste a picture here with Control V.`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          take(event.dataTransfer.files[0]);
        }}
        onPaste={(event) => {
          const item = [...event.clipboardData.items].find((entry) => entry.type.startsWith("image/"));
          if (item) {
            event.preventDefault();
            take(item.getAsFile());
          }
        }}
      >
        {imageUrl ? (
          <img src={imageUrl} alt={label} />
        ) : (
          <p className="picture-box-empty">
            Drop a picture here, paste one (Ctrl+V), or choose a file.
            {hint && <span className="picture-idea">Idea: {hint}</span>}
          </p>
        )}
      </div>
      <div className="actions">
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(event) => {
            const file = event.target.files[0];
            event.target.value = "";
            take(file);
          }}
        />
        <button type="button" className="secondary" onClick={() => input.current?.click()} disabled={busy}>
          {imageUrl ? "Change picture" : "Choose a picture"}
          <span className="visually-hidden"> for {label}</span>
        </button>
        {imageUrl && (
          <button type="button" className="danger" onClick={onRemove} disabled={busy}>
            Remove picture<span className="visually-hidden"> from {label}</span>
          </button>
        )}
      </div>
    </div>
  );
}
