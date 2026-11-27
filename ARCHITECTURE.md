# StoryBridge architecture

## Pipeline
```
 consent form ─► project (consent record)
                    │
 audio upload ──────┤  record.py: consent gate → ffmpeg → 16 kHz mono WAV, loudness normalized
                    ▼
               transcribe.py: faster-whisper (local CPU, int8) → transcript lines + word times
                    ▼
               "Make the storybook" — drafting.py picks one:
                 1. providers/gemini.py (live, if allowed) → picture-book pages, saved as ai_draft.json
                 2. providers/fixture.py (a saved draft made from THIS transcript)
                 3. structure.py: the storyteller's own words, 3 lines per page
                    ▼
               every AI sentence = not read yet ("flagged"), with source lines + recording time
                    ▼
               a person reads it ⇄ "Ask for changes" (AI rewrites; only changed sentences need reading again)
                    │              and/or "Fix this page by hand" (edit / take out)
                    ▼
               "The story is right" ── export locked until the story is confirmed
                    ▼
 photos.py ──► book_pdf.py: white 8 x 8 pages, picture box + text | print (bleed + QR) | family (no QR)
                    ▼
               book_preview.py: page pictures for the in-app page flipper (stamped PREVIEW until checked)
                    ▼                                    ▼
               clips.py: one MP3 per chapter      book_export.py: page pictures (ZIP)
                    ▼
               QR codes on paper play the clips from this computer (same Wi-Fi)
```

## Data model (`backend/app/schemas.py`)
Everything about one story is a single `project.json` in `data/projects/<id>/`, next to its audio, clips, photos, and books. There is no database server.

- **StoryProject**
  - Identity and consent: id, storyteller name, family name (used in the story), pronouns (chosen by a person), recording kind (`storyteller` / `self_demo` / `synthetic_dev`), and the consent record.
  - Audio and text: audio file, transcript, chapters.
  - Book: book title (a person's choice), suggested title (the AI's), cover photo, photo pages, and `drafted_by`.
  - warnings.
- **ConsentRecord:** a separate yes/no for recording, local transcription, book, voice QR codes, demo video, and outside AI, plus facility permission, withdrawn, and notes.
- **TranscriptSegment:** id, text, start and end seconds, and words with times.
- **Chapter (one page of the book):** id (`p1`, `p2`, …), the transcript lines it covers, sentences, voice-clip start and end, picture, and picture idea. The name "chapter" is historical; the interface calls them pages.
- **BookSentence:** id, text, source line ids, edit type (`verbatim`, `light_edit`, `ai_draft`, `volunteer_caption`), grounding score (none yet), and status (`approved`, `flagged` = not read and confirmed yet, `removed`). A sentence added from the family's own message has no source lines.

## Modules
| Module | Job |
|---|---|
| `main.py` | HTTP API. Requests from other devices, or passed on by a web host or tunnel, are refused except the voice-clip links. Also serves the app, and the student's redesigned SmileCard website at `/smilecard/`. |
| `services/record.py` | Consent gate, upload, ffmpeg normalization. |
| `services/transcribe.py` | Local Whisper transcription. |
| `services/structure.py` | Groups transcript lines into pages (used for the own-words book). |
| `services/drafting.py` | "Make the storybook". Decides whether live AI may run. Validates drafts (every sentence must cite real lines of this recording, otherwise nothing changes). Retries once and falls back to a saved draft or the storyteller's own words, with a warning. Only reuses a saved draft for the same transcript (fingerprint). Keeps pictures with their page number. **Ask for changes** (`revise_story`): sends the transcript, the book, and the request; keeps sentences that come back word for word (and their status), marks new or changed ones as not read, moves pictures with their page, and changes nothing if the answer doesn't fit. **The story is right** (`confirm_story`). |
| `providers/gemini.py` | The picture-book prompt (third person, 1–3 sentences per page, no new facts, cite your lines) and the change prompt (change only what was asked, copy the rest word for word, facts may come from the request). Retries on temporary errors. The key is never put in a URL or an error. |
| `providers/fixture.py` | Replays a saved draft (offline demo). |
| `services/photos.py` | Checks, straightens, and stores pictures locally. File names are chosen by the app. |
| `services/book_pdf.py` | The 8 x 8 white picture book: cover (Chewy title and picture box), one page per page of story (picture box, Arial text, page number, and a QR code in print), "The End" with the notes and the review notice. |
| `services/book_preview.py` | Page pictures for the page flipper. |
| `services/clips.py` | One MP3 per chapter for the QR codes. |
| `services/book_export.py` | Page pictures for photo-book sites (pypdfium2). |
| `frontend/` | React screens for each step, review, pictures, preview, and share. `npm run build:hosted` makes the public website's copy, which shows `HostedNotice.jsx` instead of the story tools and never calls the server. |
| `vercel.json`, `.vercelignore` | The public website on Vercel: that copy at `/` and the SmileCard website at `/smilecard/`. The server is not deployed. |
| `smilecard-site/api/feedback.py` | The live SmileCard website's only server code (a Vercel function): checks a feedback message and saves it in the private Blob store `smilecard-feedback` (and emails it, if Gmail is set up). |
| `smilecard-site/cards-data.js`, `card-tools.js` | Every card from the old smilecard.org galleries (made by `scripts/fetch_smilecard_cards.py`), and the preview, download, and favourites helpers. |

## Safeguards, in order
1. **Consent gate.** No audio is stored without consent, and withdrawal deletes everything.
2. **Local transcription.** Audio never leaves the computer.
3. **Outside-AI gate.** A real storyteller's text goes to Google only with specific consent **and** a paid-plan key.
4. **Draft validation.** Sentences must cite real lines from their own chapter.
5. **A person confirms the story.** Every AI sentence starts as not read, and export is blocked until a person presses "The story is right". A later change needs reading and confirming again.
6. **Disclosure.** The book says AI helped draft it and that a person read and confirmed it.

**Planned but not built:** an automatic fact check that would flag sentences adding or changing names, numbers, dates, negations, or people compared with the cited lines.

## Fallback paths
| Failure | What happens |
|---|---|
| No API key, or Google is unreachable or overloaded | The saved draft is used, with an on-screen warning. A successful live draft is saved for next time. |
| No internet at all | Everything except live AI drafting works. |
| Phone not on the same Wi-Fi | QR codes don't play. The family edition has none, and the print edition explains this. |
| Bad AI answer | One retry. If it still fails, the error is shown and nothing changes. |
| "Ask for changes" can't use the AI | The chat says why (no key, no consent, or Google failed), nothing changes, and changes can be made by hand. |
