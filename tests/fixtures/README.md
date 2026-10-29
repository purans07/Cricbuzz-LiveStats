# API test fixtures

normalized_match.json is authored synthetic data using this application's normalized snapshot schema version 1. It is not a captured response from Cricbuzz, RapidAPI, API.market or any other data service.

The fictional fixture exercises source identity, teams, player profiles, series/venues, two innings, performances, memberships and separate career aggregates. Its metadata marks the provider as synthetic-training, version normalized-v1. The fixture CLI always treats it as synthetic, so ingestion accepts only a sample-mode database.

Transport tests use injected responses and no network. A future vendor adapter needs separate sanitized actual-response fixtures identifying listing, API version, operation, capture time, HTTP outcome and mock/provider provenance. Never store secret headers or credential-bearing URLs here.

cricbuzz_v2_live_user_capture.json is a separate user-supplied body copied from the selected RapidAPI cricketapilive/cricbuzz-cricket v2 matches/live playground. The accompanying screenshot showed HTTP 200. Unlike normalized_match.json, this body is not authored synthetic data. No request/response headers were supplied, so gateway-mock status and exact transport route remain unverified. The capture is replayed only in isolated tests; it is not fetched again by the suite.
