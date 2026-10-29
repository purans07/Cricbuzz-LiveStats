# Phase 14 — Error Handling

Phase 14 reviews and strengthens failure handling across the existing application. It does not replace validated service boundaries or change analytical definitions. Phase 15 testing remains the next learning phase; targeted regression checks accompany these fixes now.

## Concepts explained before implementation

An exception reports that an operation cannot complete normally. Expected failures—invalid input, unavailable data, rejected access, stale versions or provider limits—need actionable recovery at the layer that understands them. Unexpected programming/rendering failures need a safe final page boundary. An empty query is a successful read with no qualifying rows, not an exception.

Catch specific failures near the responsible operation, preserve transaction cleanup, and never report success before commit. Avoid broad catches around every function; that can hide faulty logic or turn failed imports into apparent successes. A broad ordinary-Exception catch is appropriate only at the final presentation boundary, after resources/transactions have unwound. Do not catch BaseException: Streamlit rerun/stop, keyboard interrupts and process exits are control flow rather than ordinary page errors.

## Failure map and recovery

| Category | Existing/new handling | User recovery |
| --- | --- | --- |
| Configuration | Validated application/API settings, safe setup messages | Review Home's setup guides; edit private configuration outside the UI |
| Missing/incompatible database | Existing-file read-only open, mode/schema validation; no implicit initialization | Check selected target; explicitly initialize/migrate using documented tools |
| Database connection/locking | SQLAlchemy/database exceptions, transaction unwinding, safe page/action messages | Wait if locked; review local target/access and reload |
| Integrity/relationships | Foreign keys, unique/check constraints and service validation; atomic rollback | Correct innings/team/player identity or conflicting record; restore instead of recreating a tombstone |
| Stale edits | Expected-version compare inside the write transaction | Reload, inspect the newer record and deliberately reapply changes |
| Provider authentication | APIError authentication, no blind retry | Check private key and subscription; do not paste credentials into forms/chat |
| Provider rate limits | Bounded policy and Retry-After-aware cooldown | Wait; avoid repeated button clicks |
| Network/TLS/timeouts | Fixed HTTPS origin, redirect refusal, connect/read/budget limits and safe typed errors | Retry deliberately after connectivity/provider recovery; never disable certificate validation |
| Invalid/oversized JSON | Content-type/size/decode/shape checks, then provider-specific normalization | Keep the saved snapshot; investigate the provider contract rather than partially importing |
| Invalid user values | Fixed fields, strict integer/date/flag/relationship checks | Correct the value; blank means unknown, not zero |
| Expensive/custom SQL | Read-only authorizer, one statement and time/value/result limits | Use supported reads, simplify or narrow the query |
| Empty chart/query/filter | Explicit empty/coverage state | Change the filter or import sufficient history; do not invent missing data |
| Unexpected Streamlit/rendering error | New shared route/application boundary | Reload or open Home; inspect saved records before repeating a mutation |
| HTTP client cleanup | Key reference cleared in finally, even if session close fails | A cleanup error is not evidence that a previous import did not commit |

## Database exceptions and transaction safety

The existing Database manager supplies read-only reader connections and explicit write transactions. Public-readonly mode refuses writes. Writes use BEGIN IMMEDIATE and service operations commit atomically. A raised exception inside the transaction rolls back instead of leaving a half-applied profile or scorecard import. Revision increases only after successful data changes.

The CRUD layer maps integrity violations to a safe relationship/conflict message rather than exposing raw SQL or connection URLs. StaleRecordError is distinguished from validation: a stale form must not automatically switch to the newest version and silently overwrite it. Expected versions remain the ones loaded before the edit.

The final page boundary runs after nested transaction contexts unwind, so it does not commit or manually roll back a service transaction. A failure **after** commit, during result display or resource cleanup, is different from a failed write. Its recovery message deliberately says an operation may already have committed. The operator must inspect current records before repeating it; the UI does not assert that every display error means data was unchanged.

Connections/cursors/locks are closed or released through existing finally/context-manager paths. Error handling does not initialize missing files, migrate schemas, hard-delete records, or erase last successful snapshots to hide a failure.

## API, connection and JSON errors

The existing HTTP client already validates provider/version, fixed HTTPS origin, authentication/header contract and declared endpoints; blocks redirects and unsupported queries; enforces response-size and time limits; and closes each HTTP response. Authentication, rate-limit, TLS, transport, HTTP, JSON, shape and normalization failures are distinguishable through safe APIError codes.

Retries remain bounded by the reviewed policy and budget; nonretryable authentication, malformed JSON and validation failures do not get blanket retries. Requests stay outside database write transactions. The normalizer validates provenance, expected identifiers, scope and record shape before ingestion. Existing mock-response checks and source isolation remain in force.

A syntactically valid JSON document is not automatically a valid scorecard. Missing/wrong fields, stale or incompatible scopes and incorrect match/player identity must still be rejected. Likewise an empty valid match list is not a JSON error. Do not catch decode failures and substitute an empty list, fabricate zeros or claim a successful refresh.

Live Matches continues to keep saved data after request/import failure, show that no successful refresh is claimed, and use process-local cooldown/Retry-After protection. This milestone adds a coded diagnostic event to these API failures without logging raw bodies, URLs, keys or exception text.

The client close method now clears its retained credential reference in a finally block. Previously, a failing session.close could skip that assignment. Cleanup failure still propagates as an ordinary error, and coordinator locks are released by their own finally block. Clearing a Python reference is not a guarantee of secure memory erasure or removal of every copy held by a library.

## Validation errors

Keep user-facing validation at the form and repeat authoritative rules in services/database constraints. Current rules distinguish blank from known zero, reject inappropriate integer types/negative values, validate dates/timezones, enforce cricket units, protect identities/source fields and verify innings/team/participation relationships.

The existing CRUD form still shows actionable safe service ValueErrors and ownership messages. Analytics still shows its bounded read-query errors. The final boundary does not replace them with a generic message. Numeric/ratio/display fallbacks must not transform unknown or undefined inputs into misleading zero performance.

## Streamlit errors and control flow

Every route now wraps its render call with `page_error_boundary(scope)`. The main entry point also wraps page.run so ordinary route execution/import/render failures reaching that level get a safe final response. The boundary catches Exception, logs an allowlisted event classification and renders a generic error plus recovery guidance. It never displays `st.exception(error)` or a raw traceback to a visitor.

Streamlit's installed RerunException and StopException inherit BaseException. They therefore pass through unchanged, as do KeyboardInterrupt and SystemExit. Existing CRUD post-commit reruns and form behavior remain operational; the boundary does not intercept them as failures. Startup failures before Streamlit/dependencies/boundary imports are available remain terminal/deployment problems, not errors this UI can render.

This is a final recovery layer, not a claim that unexpected programming errors are fixed by catching them. Partial page content can remain visible before the safe error. Reloading should rebuild state; before retrying an edit or refresh, inspect saved records because backend work may already have completed.

## Safe diagnostic logging

`utils/logging_config.py` now emits project-specific warning events through a dedicated nonpropagating logger. Event, code and scope are all selected from fixed vocabularies. Unrecognized caller values become generic allowlisted tokens. The logger never receives the exception object, traceback, SQL statement, response payload, request headers, key fragment, database URL or arbitrary context dictionary.

Example diagnostic vocabulary:

```text
event=api_refresh code=authentication scope=Live Matches
 event=crud_write code=stale_record scope=CRUD
 event=page_render code=unexpected scope=Home
```

API refresh failures, CRUD stale/database failures and final page failures use this path. Expected inline validation messages need not become noisy diagnostic logs. The dedicated logger does not modify root logging or claim to sanitize every third-party library in the process. In particular, do not independently enable HTTP wire/debug logging with real credentials.

Handler setup is lock-protected to avoid duplicate handlers on concurrent first use. The console handler writes to the current stderr and tolerates an unavailable/closed console so diagnostic output cannot break recovery. It creates no log file or external telemetry destination. Deliberately omitting raw traces reduces diagnosis detail; a trusted operator can reproduce a bug with synthetic/test settings and targeted tests rather than publishing private execution context.

## Best practices applied

- Preserve expected typed failures and actionable messages near the operation.
- Keep final generic recovery at the page boundary; do not swallow process/control-flow exceptions.
- Use finally/context managers for resources and atomic transaction ownership.
- Validate before spending quota and before starting writes; do not hold write locks during HTTP.
- Bound retry/time/size/output costs; honor cooldown rather than repeatedly retrying.
- Keep empty, stale, partial, unknown and failed states distinct.
- Never claim rollback merely because rendering failed after an operation.
- Log safe event codes, not credentials, raw SQL, bodies or exception traces.
- Verify failure behavior with injected errors and temporary data, not deliberate failures against a paid provider or working database.

## Files and verification

Changed/created files: `ui/errors.py`, `utils/logging_config.py`, all six route scripts, main.py, API client cleanup, Live Matches/CRUD diagnostic calls, `tests/test_error_handling.py`, this guide and current progress documents.

Eighteen new regression cases cover exception classification, allowlisted/redacted diagnostic output, stop/interrupt/exit propagation, unexpected runtime/Streamlit/validation errors without private display details, recovery on a subsequent rerun, credential-reference clearing on failed session cleanup, rollback/revision preservation for an interrupted write and logging to an unavailable console. Existing API tests retain malformed JSON, content type, timeout, authentication, rate-limit and provenance coverage; existing CRUD/SQL/UI checks retain their own expected-failure scenarios.

The full suite passes **510 tests**, with lint, formatting and whitespace checks passing. No working sample/live records, private configuration or API quota were used to trigger failures. Tests run against injected doubles and temporary databases.

**What we completed:** reviewed every requested failure category, added safe route/application recovery and coded project diagnostics, and fixed credential-reference cleanup on session-close failure.

**Concepts learned:** typed versus unexpected failures, transaction rollback versus post-commit display failure, retryability, JSON validation layers, safe logging and Streamlit's BaseException-based control flow.

**Next phase preview:** Phase 15 — Testing will organize the unit, integration, database, API and UI strategy, map important requirements to evidence, and identify remaining acceptance gaps. Phase 14 is complete; advance after the next user request.
