# CREDITS

_Draft. To be completed before submission (reminiscence-therapy references and volunteer illustrators, with their permission, still to add)._

## Fonts
- **Chewy** by Squid Art Factory, Apache License 2.0, see `assets/fonts/LICENSE-Chewy.txt`. Bundled in `assets/fonts/`. Used for the book's titles; chosen by the student as the closest free match to the "children's book" lettering they wanted. Downloaded unmodified from Google's official font repository (https://github.com/google/fonts).
- **Arial** (Microsoft) for the book's story text, read from Windows' own font folder at run time and **not** bundled, because its license doesn't allow redistribution. On computers without Arial the PDF uses Helvetica, which looks the same.
- Earlier versions used Lora and Playfair Display; they were removed on 2026-11-21.
- **App screens** (not the book) use **Instrument Serif**, **Outfit**, **Pacifico** (the SmileCard name), and **Patrick Hand** (the handwriting in the logo), all SIL Open Font License, installed locally from the `@fontsource` npm packages, so the app needs no internet. They are the fonts of the student's SmileCard website redesign.

## SmileCard website and artwork
- `smilecard-site/` holds the student's redesign of the SmileCard website (from a zip the student shared on 2026-11-22). Claude added a "StoryBridge" item to its menus (`PageHero.dc.html`, `SmileCard Home v7.dc.html`) and an `index.html` that opens the home page, and moved the bobbing mascots' shadows onto the mascots themselves so scrolling is smoother (same look); the rest is unchanged. Older home-page versions and screenshots from the zip were not copied.
- Its pages run on the design's own `support.js`, which loads React, ReactDOM, and Babel from unpkg.com, and they load fonts from Google Fonts and pictures from smilecard.org, so they need internet.
- The SmileCard logo and the smiling-card friends in the app (`SmileCardArt.jsx`) are copied from that redesign's code.
- **Mountain photo** (`hero-mountains.jpg`): from the redesign. _Source and license: to be confirmed by the student before publishing._

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
