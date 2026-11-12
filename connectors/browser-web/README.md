# `browser-web` Connector

**Target Programs:** Brave Browser (Default) and Firefox.

## Control API
- **Primary Bridge:**
  - **Brave (Chromium):** Chrome DevTools Protocol (**CDP**) over local debugging port + Native Messaging host extension.
  - **Firefox:** WebDriver BiDi / Marionette + Native Messaging host.
- **Planned Tools:**
  - `list_tabs` / `read_page_content` (`read`): Inspect open tabs, active URL, and page text/DOM summary.
  - `open_url` / `organize_tabs` (`write`): Open URLs, group tabs, or bookmark pages.
  - `automate_page` (`privileged` when submitting forms): Click/fill forms only under explicit policy approval.
