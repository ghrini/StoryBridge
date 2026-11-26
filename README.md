# StoryBridge

StoryBridge turns an older person's spoken memories into a short, illustrated keepsake storybook. A volunteer records the storyteller (with consent), StoryBridge turns the recording into text on the computer, AI drafts the story as picture-book pages, and **a person reads the whole story with the storyteller or family and confirms it** before the book can be printed or shared. Changes are asked for in plain words, in a chat box. Each chapter can carry a QR code that plays the storyteller's own voice.

It is built for **SmileCard**, a student nonprofit that sends cards and art to isolated seniors and patients.

> StoryBridge is a consent-first workflow that turns a senior's recorded memories into an illustrated keepsake storybook. AI drafts the story, every sentence links back to the moment in the recording it came from, and a person must read and confirm the story before it can be printed or shared.

StoryBridge is not the first life-story app (products such as Remento and StoryWorth exist). Its focus is the review step: the story reads like a book, yet nothing reaches the family until a person has read it and confirmed it is right.

## The problem and who it's for
- **Storytellers:** older adults who want their memories kept for family, especially those who are isolated.
- **Volunteers and families:** they record, review, and add photos or drawings.
- **Why review matters:** AI story writers tend to embellish. On our test stories the AI changed "we" to "her friends" and "we had two cows" to "he had two cows". These are small, but in someone's real life story they matter.

Research on reminiscence interventions suggests a small-to-moderate benefit for depressive symptoms in older adults (see CREDITS.md). **StoryBridge itself has not been clinically evaluated and makes no health claims.**

## What it does
1. **Consent first.** Each permission is a separate yes/no box: recording, transcription on this computer, making a book, voice QR codes, the demo video, and sending text to an outside AI. Withdrawing deletes everything.
2. **Recording to text.** Upload audio. It is normalized with ffmpeg and transcribed **on this computer** by Whisper (faster-whisper), with word timestamps. Audio never leaves the computer.
3. **One button: "Make the storybook".** Google Gemini splits the story into picture-book pages written **about** the storyteller, using the name the family uses and the pronouns a person chose. Each page has 1–3 sentences and a picture idea, and the book gets a title. Every sentence cites the transcript lines it came from.
   - If the AI may not be used (for example, no consent to send the text out), the pages use the storyteller's own transcribed words instead.
4. **Read it and ask for changes.** The volunteer reads the pages with the storyteller or family.
   - **Ask for changes:** type what's wrong in plain words ("her friend's name is spelled Dotty", "make page 3 shorter") and the AI rewrites the book. Only new or changed sentences are marked **changed**; everything else comes back word for word, and pictures stay with their pages.
   - **Fix this page by hand** (folded away under each page): each sentence's recording time, a **Play source** button, **Edit**, and **Take out**.
   - **The story is right:** one button confirms the whole story. Printing and sharing stay locked until then, and a later change needs confirming again (only the changed sentences need reading).
5. **Pictures.** Every page, and the cover, has a picture box. Choose a file, drag one in, or paste one copied from anywhere (Ctrl+V). An empty box prints as a frame, so the family can draw or glue in a photo.
6. **Book and sharing.**
   - **Page flipper:** shows the book as an open book with turning pages.
   - **Print edition:** 8 x 8 inch white pages with 1/8 inch bleed, plus a small voice QR code on each page.
   - **Family edition:** trimmed, with no QR codes.
   - **Page pictures:** 2400 x 2400 pixel images for photo-book sites.
   - **Share button:** opens the device's share menu (WhatsApp appears if installed) and falls back to a download.

## Setup on Windows (PowerShell)
Prerequisites: Python 3.11, Node.js 20 or newer, Git, and ffmpeg.

```powershell
winget install --id Gyan.FFmpeg --exact      # then open a NEW terminal so ffmpeg is on PATH
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend; npm install; npm run build; cd ..
Copy-Item .env.example .env                  # optional settings; see the comments inside
```

Optional settings in `.env`:
- **`GEMINI_API_KEY`** turns on live AI story writing. Without it, StoryBridge still works with saved drafts.
- **`BASE_URL`** is this computer's network address (for example `http://192.168.1.20:8000`), so phones on the same Wi-Fi can play the QR codes.

The first transcription downloads the Whisper `small` model weights (no audio is sent) into `models/`.

## Run
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```
Open **http://127.0.0.1:8000** on this computer. If Windows asks about the firewall, allow private networks only, so phones can reach the QR clips.

The redesigned SmileCard website is at **http://127.0.0.1:8000/smilecard/**. Its menu has a **StoryBridge** item that opens the app, and the app's menu links back. The website's pages load React and fonts from the internet when opened; the StoryBridge app itself works offline.

**Demo recordings** (computer voice reading fictional stories; never presented as real people):

```powershell
powershell -File scripts\make_synthetic_clip.ps1                       # "Pop" sample -> data\dev\SYNTHETIC_story.wav
powershell -File scripts\make_synthetic_clip.ps1 -TextPath fixtures\demo_story_gram.txt -OutPath data\dev\DEMO_gram_story.wav
```

Create a story of kind "Computer-voice test", upload a clip, fill in step 2, and press **Make the storybook**.
- **"Pop" sample:** has a saved AI draft in `fixtures/drafts/`, so it works with **no key and no internet**. A saved draft is only reused for the exact transcript it was made from.
- **Other stories:** need the key once. Each live draft is then saved in the story's folder and replays offline afterwards.

## Tests
```powershell
.\.venv\Scripts\python.exe -m pytest        # backend and the SmileCard feedback function: 208 tests
cd frontend; npm test                        # frontend: 9 tests
```
Backend tests never call Google; a mock network is used. Counts are as of 2026-11-24.

## Privacy decisions
- **Recordings, transcripts, photos, and books stay on this computer** (`data/`, which is never committed to git).
- **Only text is ever sent to the AI, never audio:** the transcript, plus the book's text and the volunteer's message when they ask for changes. A real storyteller's text is sent only if they specifically agreed **and** the key is declared a paid Google plan. Google may use text sent through free keys to improve its products, and people there may read it.
- **On the Wi-Fi, a phone can reach only the voice clips** the QR codes link to. It cannot list projects, read transcripts, see photos, or download books.
- **A request passed on by a web host or tunnel never counts as coming from this computer**, because those pass every visitor on from 127.0.0.1.
- **Withdrawal deletes the whole project folder.**
- **Health details, addresses, financial details, and other people's private information must stay out of the book.** The AI is told to leave them out, and the reviewer checks.
- **The API key stays on the server.** It is never sent to the browser and never written into error messages.

## Public website on Vercel
`vercel.json` puts two parts on Vercel as one project:

| Service | Folder | Address | What it is |
|---|---|---|---|
| `frontend` | `frontend/` | `/` | The StoryBridge page for visitors (`npm run build:hosted`). It explains StoryBridge and has no upload form and no server to call. |
| `smilecard` | `smilecard-site/` | `/smilecard/` | The SmileCard website. |

- **The StoryBridge server (`backend/`) is not on Vercel.** Recordings and stories are promised to stay on the volunteer's computer, and there are no logins. It also does not fit: its libraries are 476 MB for Linux (the limit is 500 MB) before ffmpeg and the speech model, uploads are limited to 4.5 MB, and it keeps stories as files on disk.
- **No service calls another**, so there are no bindings.
- **`.vercelignore` is an allow-list.** Only those two folders and `vercel.json` go to Vercel. Keep it: without it, `vercel dev` hands out files from `data/`.
- **To test:** `npx vercel@65.8.0 dev --local --listen 127.0.0.1:3000`. On this Windows computer 66.6.0 stopped with a symlink permission error. Without `--listen`, other devices on the Wi-Fi can open it.

## The live SmileCard website
The SmileCard website is its own Vercel project whose Root Directory is `smilecard-site/`, so the `vercel.json` above is not used by it. **Every push to `main` goes live.**

- **Cards:** `cards-data.js` lists every card in the galleries of the old smilecard.org, in the same order: Recent Cards (946), All Cards (2,177), the six categories, and Jacob's Heart (78); 3,188 different cards. Rebuild it with `.\.venv\Scripts\python.exe scripts\fetch_smilecard_cards.py`. It keeps only image ids, not file names (many contain volunteers' names).
- **Pictures and videos are still hosted by Wix** (`static.wixstatic.com`, `video.wixstatic.com`). If the Wix site is deleted they may stop loading, so copy them somewhere else first.
- **Favourites** (♡) are saved in the visitor's own browser. **Downloads** (↓) use Wix's `?dn=` link, which makes the browser save the file.
- **Forms:** submitting cards, service hours, and leadership applications stay Google Forms, so answers keep going to SmileCard's Google account.
- **Feedback form → email:** `api/feedback.py` (Python, standard library only) emails each message from the Testimonials page to SmileCard's Gmail, with the visitor as Reply-To. It stores nothing and logs no personal details. It needs these in Vercel (Settings → Environment Variables, marked Sensitive):
  - `SMTP_USER`: the Gmail address that sends the emails.
  - `SMTP_APP_PASSWORD`: a Gmail app password for it (Google Account → Security → 2-Step Verification must be on → App passwords). Never put it in the code.
  - `FEEDBACK_TO` (optional): where messages go; defaults to `SMTP_USER`.

  Without them the form tells the visitor it could not send and shows the email address instead.
- **Spam:** a hidden field, a 2-second minimum, a same-site check, and 5 messages per address per 10 minutes (per running copy of the function). For a firm limit, add a rate-limit rule in Vercel Firewall.

## Accessibility decisions
- StoryBridge is one page of the SmileCard website (the student's redesign), all on one scroll:
  - the SmileCard menu and a banner with the hills drawing
  - "How it works"
  - "Your stories" and "Start a new story" side by side
  - the open story below
- Large type (20 px base), high contrast, and big pill buttons.
- Labelled form fields and visible focus outlines.
- Status and error messages announced to screen readers.
- Changed sentences are highlighted **and** labelled "changed"; taken-out sentences say "✕ Taken out of the book". Never colour alone.
- The book's story text is Arial, at 14–17 pt, black on white. Titles use Chewy.
- Not yet verified: keyboard-only use of every step and screen-reader testing (see limitations).

## Evaluation (real measurements only)
- **Transcription speed** (Whisper `small`, int8, on an AMD Ryzen 9 9950X3D): 1.7–2.4 s for a 29.4 s recording of the student's voice (0.06–0.08 x real time). `medium` took 21.4 s for the same clip. Raw numbers: `eval/whisper_benchmark.json`.
- **AI drafting** (Gemini `gemini-3.5-flash`, fictional test stories only):
  - It invented no new events.
  - It did make small changes a reviewer must catch: "we" became "her friends" or "everyone", "we had two cows" became "he had two cows", and a picture idea said "fresh rolls" where the rolls were burned.
  - A full 22-line story took about 12 s through the interface (one run).
  - **Ask for changes** (one run, fictional "Pop" story): asked to respell a friend's name on page 3 and add a detail, it changed only page 3 and returned every other sentence word for word. The answer arrived within 30 s.
- **Not measured yet:** an automatic fact check's precision and recall (it does not exist yet), feedback from real storytellers or families (none collected), printed output quality, and the real WhatsApp share menu.

## Known limitations
- **No real storyteller has used it yet.** The demo story is fictional, read by a stock computer voice, and labeled as such in the book.
- **No automatic fact check yet.** The person reading the story is the only safeguard against AI changes.
- **"Ask for changes" needs the AI** (a key, internet, and, for a real storyteller, their consent). Without it, changes are made by hand. The chat itself is not saved; the changes are.
- **A sentence added from the family's message has no recording behind it.** It is marked "From a message you sent", and a page made only of such sentences has no voice QR code.
- **Transcription errors.** Speech-to-text makes mistakes, especially on quiet or unclear recordings, and the reviewer has to catch them.
- **QR codes only work on the home Wi-Fi** while the StoryBridge computer is running.
- **Own-words pages can split a sentence.** Without AI, each page takes three transcript lines as they are, and speech-to-text lines can end mid-sentence.
- **In-browser recording is not built yet.** Recordings are uploaded as files.
- **Untested outside Windows.**

## Documents
- `ARCHITECTURE.md`: how it works.
- `AI_USE.md`: what Claude wrote and what the student wrote.
- `CREDITS.md`: fonts, models, libraries, research.
- `docs/CONSENT_FORM.md`: consent template.
- `docs/VIDEO_PLAN.md`: plan for the 3-minute video.
