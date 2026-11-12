# `office-okular` Connector

**Target Programs:** `Okular` (PDF, EPUB, DjVu, ComicBook viewer) + `poppler` (`pdftotext`/`pdfinfo`).

## Control API
- **Primary Bridge:** `Okular` D-Bus interface (`org.kde.okular*`) for opening/navigating pages + `poppler` CLI for fast structured text & metadata extraction.
- **Planned Tools:**
  - `inspect_pdf` / `extract_text` (`read`): Read page count, metadata, and text from specific page ranges.
  - `open_at_page` (`write`): Open a document in Okular directly on the requested page or search term.
