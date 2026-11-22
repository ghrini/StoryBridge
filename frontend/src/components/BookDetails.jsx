import { useState } from "react";

/** What the family calls the storyteller, their pronouns (chosen by a person, never guessed), and the title. */
export default function BookDetails({ project, onSave, busy }) {
  const [familyName, setFamilyName] = useState(project.family_name ?? "");
  const [pronouns, setPronouns] = useState(project.pronouns ?? "");
  const [title, setTitle] = useState(project.book_title ?? "");

  function submit(event) {
    event.preventDefault();
    onSave({ family_name: familyName, pronouns: pronouns || null, book_title: title });
  }

  return (
    <form onSubmit={submit} className="stack">
      <div className="field">
        <label htmlFor="family-name">What the family calls the storyteller (used in the story, for example Gram, Nana, or Grandpa Joe)</label>
        <input id="family-name" type="text" value={familyName} onChange={(event) => setFamilyName(event.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="pronouns">Pronouns to use in the story</label>
        <select id="pronouns" value={pronouns} onChange={(event) => setPronouns(event.target.value)}>
          <option value="">Choose…</option>
          <option value="she/her">she / her</option>
          <option value="he/him">he / him</option>
          <option value="they/them">they / them</option>
        </select>
      </div>
      <div className="field">
        <label htmlFor="book-title">Book title (optional)</label>
        <input
          id="book-title"
          type="text"
          value={title}
          placeholder={project.suggested_title ?? ""}
          aria-describedby="book-title-hint"
          onChange={(event) => setTitle(event.target.value)}
        />
        <p id="book-title-hint">
          {project.suggested_title
            ? `Leave this blank to use the suggested title: “${project.suggested_title}”.`
            : "Leave this blank and a title will be suggested when the story is drafted."}
        </p>
      </div>
      <button type="submit" disabled={busy}>
        Save book details
      </button>
    </form>
  );
}
