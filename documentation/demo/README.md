# Updated project walkthrough

[Play the fresh walkthrough](cricbuzz-walkthrough.mp4).

Recorded 29 October 2026 after the navy/emerald theme and simplified Home/Top Players changes. The silent 57.5-second MP4 contains actual browser screenshots at two frames per second, encoded as H.264; mobile captures are letterboxed. No narration, fabricated data frames or live API request is included.

## Demonstrated flow

- Home welcome, dataset counts and compact documentation links.
- Saved match selection and innings scorecard.
- Player rankings and chart.
- A saved SQL execution and quarterly visualization.
- Player creation in a disposable fictional sample.
- Settings database status and mobile Top Players.

All six pages rendered without browser page errors or Streamlit exceptions. The recording uses an isolated schema-2 sample database under /tmp and a separate local operator server on port 8505. The working sample/live databases were not edited. Only the disposable sample received the player creation. This demonstrates the full local mode; the public website intentionally disables administrative writes, custom SQL and provider refreshes.

[Verification metadata](verification.json) · [Local/public mode comparison](../live_refresh_and_demo.md). API refresh behaviour has separate tests and dated authenticated evidence; this fictional-data walkthrough does not prove current provider availability. Tests also cover updates, deletes, restore and failure paths not all visually demonstrated in this short recording.
