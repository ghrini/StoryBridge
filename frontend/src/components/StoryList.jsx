import { KIND_LABELS, formatTime } from "../services/format.js";

/** The stories on this computer, each with an Open button. */
export default function StoryList({ projects, openId, onOpen }) {
  if (projects === null) return <p>Loading your stories…</p>;
  if (projects.length === 0) return <p>No stories yet. Start one in the form next to this.</p>;
  return (
    <ul className="story-list">
      {projects.map((project) => {
        const name = project.book_title || project.family_name || project.storyteller_name || "Unnamed storyteller";
        const isOpen = project.id === openId;
        return (
          <li key={project.id} className={isOpen ? "is-open" : ""}>
            <div>
              <strong>{name}</strong>
              <span>
                {KIND_LABELS[project.recording_kind]}
                {project.duration_seconds != null && <> · {formatTime(project.duration_seconds)} long</>}
                {project.pages > 0 && (
                  <>
                    {" "}
                    · {project.pages} {project.pages === 1 ? "page" : "pages"}
                  </>
                )}
              </span>
            </div>
            <button type="button" className="pill-pink" onClick={() => onOpen(project.id)} aria-current={isOpen || undefined}>
              {isOpen ? "Open below" : "Open"}
              <span className="visually-hidden"> {name}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
