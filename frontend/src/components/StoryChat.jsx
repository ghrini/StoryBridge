import { useEffect, useRef, useState } from "react";

/** The page numbers that changed, as words: "page 3", "pages 2 and 5", "pages 2, 3, and 6". */
function pageList(pages) {
  if (pages.length === 1) return `page ${pages[0]}`;
  const last = pages[pages.length - 1];
  const rest = pages.slice(0, -1);
  return `pages ${rest.join(", ")}${rest.length > 1 ? "," : ""} and ${last}`;
}

/**
 * "Ask for changes": after reading the story, the reviewer says what to change in their own words and the
 * AI rewrites the book. Changed sentences are marked in the pages so they can be read again.
 */
export default function StoryChat({ name, helper, busy, onAsk }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const log = useRef(null);
  const examples = [
    "Page 3: her friend's name is spelled Dotty.",
    "Make page 2 shorter and more fun.",
    `Add a last page: "We love you, ${name || "Gram"}!"`,
  ];

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [messages]);

  async function send(event) {
    event?.preventDefault();
    const request = text.trim();
    if (!request || busy) return;
    setMessages((all) => [...all, { from: "you", text: request }]);
    setText("");
    const result = await onAsk(request);
    if (result.error) {
      setMessages((all) => [...all, { from: "helper", text: result.error, problem: true }]);
      setText(request); // nothing changed, so keep their words to try again
      return;
    }
    const pages = result.changed_pages;
    const note = pages.length ? `Changed ${pageList(pages)}. Read the parts marked “changed”.` : "Nothing in the book changed.";
    setMessages((all) => [...all, { from: "helper", text: result.reply || "Done.", note }]);
  }

  return (
    <div className="chat">
      <h4 id="chat-title" className="chat-title">
        Ask for changes
      </h4>

      {helper && !helper.available ? (
        <p className="chat-off">
          The AI helper can&rsquo;t be used for this story. {helper.reason} You can still fix words yourself: open
          &ldquo;Fix this page by hand&rdquo; under any page.
        </p>
      ) : (
        <>
          <div className="chat-log" ref={log} role="log" aria-live="polite" aria-labelledby="chat-title">
            {messages.length === 0 ? (
              <p className="chat-hello">
                Read the story, then tell me what to change, in your own words. For example:
              </p>
            ) : (
              messages.map((message, index) => (
                <div key={index} className={`chat-msg chat-${message.from}${message.problem ? " chat-problem" : ""}`}>
                  <span className="visually-hidden">{message.from === "you" ? "You said: " : "StoryBridge: "}</span>
                  {message.problem && <span aria-hidden="true">⚠ </span>}
                  {message.text}
                  {message.note && <span className="chat-note">{message.note}</span>}
                </div>
              ))
            )}
            {busy && messages.length > 0 && messages[messages.length - 1].from === "you" && (
              <p className="chat-msg chat-helper chat-thinking">Changing the story… this can take up to a minute.</p>
            )}
          </div>

          {messages.length === 0 && (
            <div className="chat-examples">
              {examples.map((example) => (
                <button key={example} type="button" className="chat-example" onClick={() => setText(example)}>
                  {example}
                </button>
              ))}
            </div>
          )}

          <form className="chat-form" onSubmit={send}>
            <label htmlFor="chat-input" className="visually-hidden">
              What would you like to change?
            </label>
            <textarea
              id="chat-input"
              rows={3}
              value={text}
              maxLength={1000}
              placeholder="What would you like to change?"
              onChange={(event) => setText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) send(event);
              }}
            />
            <button type="submit" disabled={busy || !text.trim()}>
              Send
            </button>
          </form>
          <p className="chat-privacy">
            Only the story&rsquo;s words and your message go to Google&rsquo;s AI, never the recording. Please
            don&rsquo;t type addresses or health or money details.
          </p>
        </>
      )}
    </div>
  );
}
