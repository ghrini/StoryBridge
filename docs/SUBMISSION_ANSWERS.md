# Submission answers: notes and questions

_The Congressional App Challenge wants **your** words. Claude has **not** written your answers. This file holds facts you can use and questions only you can answer. Check the official submission form for the exact questions and word limits._

## Facts you can use (all true as of 2026-10-24)
- **What it does:** turns a senior's recorded memories into an 8 x 8 inch illustrated storybook. Local transcription; AI-drafted story; every sentence linked to the recording; a person reads the story, asks for changes in plain words, and confirms it before it can be shared; photos and drawings; a print edition with voice QR codes; a family edition; page pictures for photo-book sites; a share button.
- **Built with:**
  - Backend: Python 3.11, FastAPI, faster-whisper (Whisper), ffmpeg, ReportLab, pypdfium2.
  - Frontend: React and Vite.
  - AI: Google Gemini (gemini-3.5-flash).
- **Privacy:** audio never leaves the computer; outside AI only with specific consent and a paid key; withdrawal deletes everything; phones on the Wi-Fi can only play voice clips.
- **Real measurements:**
  - Transcription: 1.7–2.4 s for a 29.4 s clip (Whisper small on CPU).
  - Tests: 157 backend and 14 frontend.
  - AI drafting: invented no new events in test stories, but made small changes ("we" became "her friends") that review catches.
- **AI disclosure:** Claude (Anthropic) wrote the code with you directing the product decisions, and Gemini drafts story text at runtime. See AI_USE.md and fill in its "student wrote" and "can explain" fields honestly.

## Questions only you can answer
1. Why did you start SmileCard, and why does this app matter to you?
2. Who would use it first? (A real grandparent, a SmileCard partner facility, ...)
3. What decisions did **you** make, and why? For example: storybook instead of a transcript; third person; review before export; privacy rules; 8 x 8 book.
4. What was the hardest problem, and how would **you** explain it to a judge?
5. What did you learn?
6. What would version 2 add? (A real storyteller pilot with consent, the automatic fact check, in-browser recording, hosting so QR codes work anywhere, ...)
7. Your congressional district. **Confirm it in the registration system before you write anything about it.**
