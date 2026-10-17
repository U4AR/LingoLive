# Project explanation PDF

[LingoLive — How it works](LingoLive-How-It-Works.pdf) is an eight-page English,
16:9 presentation covering the problem, learner flow, Google AI/Cloud Run
architecture, contextual replies, local memory, key sessions, costs, validation
and submission handoff. Links in the final page are clickable.

The editable source is `how-it-works.html`. It uses system fonts and the existing
prepared-example screenshot in `validation/web-word-bubble.png`; no external
fonts, model calls or secret values are needed to generate it.

From the project root, with Playwright and Chromium available:

```bash
node tools/render_project_pdf.cjs
```

Set `CHROMIUM_PATH` to override `/usr/bin/chromium`. Optionally set
`PDF_PREVIEW_DIR` to a temporary output directory to render page PNGs. The renderer
serves only the document and screenshot over an ephemeral loopback listener,
blocks external web requests, checks for missing images/overflow and writes the
PDF. It does not serve a public preview or access the Google APIs.

The deployment status, repository visibility and verification statements describe
October 17, 2026. Update those statements before reusing this document after a
new deployment. Web 1.4 is live as revision `lingolive-00008-cos`; current hosted
Google transcription and a context lesson are verified. This does not establish
physical-phone or valid personal-key inference quality. This document does not
claim a completed event submission or a published demo video.
