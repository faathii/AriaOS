# `comms-thunderbird` Connector

**Target Programs:** Mozilla Thunderbird (Email, Calendar, Contacts).

## Control API
- **Primary Bridge:** Local Thunderbird WebExtension / Native Messaging bridge + read-only SQLite/Mork/ICS profile inspection (never sending emails without explicit confirmation).
- **Planned Tools:**
  - `search_messages` / `list_upcoming_events` (`read`): Query inbox headers, unread counts, and calendar events.
  - `compose_draft` (`write`): Open or save an email draft for user review.
  - `send_email` (`privileged`): Send an email only after explicit user approval.
