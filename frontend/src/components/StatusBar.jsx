/** Two always-present live regions, shown as a small message at the bottom of the screen so they are
 *  visible wherever you are on the page. Errors carry a warning icon and the word "Problem", never colour alone. */
export default function StatusBar({ status }) {
  return (
    <div className="status-area">
      <p role="status" aria-live="polite" className="status">
        {status.kind === "info" ? status.text : ""}
      </p>
      <p role="alert" className="status status-error">
        {status.kind === "error" ? (
          <>
            <span aria-hidden="true">⚠ </span>Problem: {status.text}
          </>
        ) : (
          ""
        )}
      </p>
    </div>
  );
}
