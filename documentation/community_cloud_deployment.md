# Streamlit Community Cloud deployment — 2026-10-29

Reviewed release uploaded to https://github.com/purans07/Cricbuzz-LiveStats-.git on main. The release was assembled separately from working Git history, excludes private configuration, working databases, raw responses and original references, and uses the tested requirements-lock.txt dependency set through requirements.txt.

## Completed verification

- Deployment startup and public-readonly tests: 6 passed.
- Actual Python 3.13 Linux Docker image built successfully.
- Container health: healthy; all six pages rendered without exceptions through installed Chrome/Playwright.
- Restart succeeded; sample retained 72 matches and SQLite integrity_check returned ok.
- No API credentials are required for the fictional public portfolio demo.

## Cloud settings

Open https://share.streamlit.io/ in the user's signed-in session, create an app and select:

- Repository: purans07/Cricbuzz-LiveStats-
- Branch: main
- Main file path: cloud_app.py
- Advanced settings / Python version: 3.13
- Secrets: leave empty for this sample demo.

Alternatively use Paste GitHub URL with https://github.com/purans07/Cricbuzz-LiveStats-/blob/main/cloud_app.py . Deploy, then obtain the assigned streamlit.app URL. A logged-in cloud session is needed; a local container or GitHub upload does not prove cloud acceptance.

After cloud launch, check all six pages, sample-data labels, successful SQL question execution, charts, and absence of administrative write/custom SQL/API-refresh controls. Confirm the health endpoint and restart behavior. Public cloud deployment and its final URL are pending these steps.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy .
