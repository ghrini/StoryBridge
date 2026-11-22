# CREDITS

_Draft. To be completed before submission (reminiscence-therapy references and volunteer illustrators, with their permission, still to add)._

## Fonts
- **Chewy** by Squid Art Factory, Apache License 2.0, see `assets/fonts/LICENSE-Chewy.txt`. Bundled in `assets/fonts/`. Used for the book's titles; chosen by the student as the closest free match to the "children's book" lettering they wanted. Downloaded unmodified from Google's official font repository (https://github.com/google/fonts).
- **Arial** (Microsoft) for the book's story text, read from Windows' own font folder at run time and **not** bundled, because its license doesn't allow redistribution. On computers without Arial the PDF uses Helvetica, which looks the same.
- Earlier versions used Lora and Playfair Display; they were removed on 2026-11-21.
- **App screens** (not the book) use **Instrument Serif** (SIL Open Font License) for headlines, **Outfit** (SIL Open Font License) for text, and **Chewy** for the playful words. All three are installed locally from the `@fontsource` npm packages, so the app needs no internet. They were picked to match the SmileCard website's style.
- The smiling-card characters in the app are simple drawings made in code, inspired by SmileCard's mascots; they are not SmileCard's original artwork.

## Models and services
- **Whisper** speech-recognition models (OpenAI), run locally through `faster-whisper` (SYSTRAN) using the `Systran/faster-whisper-small` CTranslate2 conversion. Licenses to verify and list here.
- **Google Gemini** (`gemini-3.5-flash`) drafts the storybook text when a key is configured. Used under Google's Gemini API terms.

## Research on reminiscence (background only; StoryBridge itself has not been evaluated for any health effect)
- Pinquart, M., & Forstmeier, S. (2012). Effects of reminiscence interventions on psychosocial outcomes: a meta-analysis. *Aging & Mental Health.* PubMed 22304736: https://pubmed.ncbi.nlm.nih.gov/22304736
- Bohlmeijer, E. T., Smit, F., & Cuijpers, P. (2003). Effects of reminiscence and life review on late-life depression: a meta-analysis. *International Journal of Geriatric Psychiatry, 18,* 1088–1094.
- Effects of reminiscence therapy on psychological outcome among older adults without obvious cognitive impairment: a systematic review and meta-analysis (2023). *Frontiers in Psychiatry.* https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10098219/ (27 studies, 1,755 older adults).
- Summary used in the README: these reviews report small-to-moderate benefits for depressive symptoms, with differences between studies and uncertainty about how long the effects last. (Citations checked on 2026-10-24; effect sizes should be read in the original papers.)

## Demo content
- `fixtures/demo_story_gram.txt` and `fixtures/synthetic_story.txt` are **fictional** stories written by Claude (AI), read aloud by the stock Windows voice "Microsoft Zira Desktop". They are not real people.

## Libraries
- Backend: FastAPI, Starlette, Uvicorn, Pydantic, python-multipart, faster-whisper, CTranslate2, rapidfuzz, ReportLab, qrcode, Pillow, pypdfium2 (Apache-2.0 / BSD-3-Clause), httpx, pytest.
- Frontend: React, React DOM, Vite, @vitejs/plugin-react, Vitest.
- Tools: FFmpeg (Gyan.dev Windows build).
- Licenses for each still to be listed.
