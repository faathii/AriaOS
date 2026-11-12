# `office-libreoffice` Connector

**Target Programs:** LibreOffice Suite (`Writer`, `Calc`, `Impress`, `Base`).

## Control API
- **Primary Bridge:** LibreOffice **UNO API** (`pyuno` over local socket `--accept="socket,host=127.0.0.1,port=2002;urp;"`) + headless CLI (`soffice --headless --convert-to`).
- **Planned Tools:**
  - `read_document` (`read`): Extract text, sheets, or slide outlines from `.odt`, `.docx`, `.ods`, `.xlsx`, `.odp`.
  - `convert_document` (`write`): Convert office documents to PDF, DOCX, CSV, or Markdown without overwriting the source.
  - `edit_spreadsheet` / `generate_document` (`write`): Populate cells, tables, or formatted reports via UNO.
