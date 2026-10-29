# Project walkthrough

[Play or download the recording](cricbuzz-walkthrough.mp4).

A silent approximately 29-second browser walkthrough captured on 29 October 2026. It is an actual sequence of browser screenshots encoded at two frames per second, with no fabricated dashboard frames. There is no voice narration; use these notes while presenting. It demonstrates the fictional sample app, not fresh API availability. Capture ran against a separate local Streamlit server at 127.0.0.1:8503 with an isolated sample database under /tmp. The regular working sample/live databases were not written and no API request was made.

## Setup context

The project environment and reviewed synthetic seed initialized a disposable schema-2 sample database. The server used explicit DATA_MODE=sample, APP_ACCESS_MODE=local and a temporary DATABASE_URL; private API access was disabled for the demo. Normal setup is documented in [installation](../environment_setup.md). Do not publish private configuration or runtime databases with the recording.

## Chapters (approximate)

- 0–6 seconds: Home purpose, tools and sample counts.
- 6–9 seconds: saved match/innings view.
- 9–13 seconds: career source/format filters and ranking context.
- 13–20 seconds: saved SQL execution and quarterly visualization.
- 20–24 seconds: create a player in the disposable sample and observe success.
- 24–27 seconds: Settings health.
- 27–29 seconds: mobile Top Players layout.

All six pages rendered without a browser page error or Streamlit exception. Tests separately cover updates, deletes, restore, invalid input, conflict checks, API imports and database rollbacks; this short recording does not visually demonstrate every edge case. Full API-backed global history, other browsers and hosted deployment are not claimed.
