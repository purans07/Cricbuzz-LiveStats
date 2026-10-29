# Provider contracts

No live provider/version is selected or configured. provider-contract.json.example is deliberately inactive, uses the reserved example.invalid domain and has verified=false. It is not a real Cricbuzz route or working setup.

After selecting provider access, prepare a reviewed manifest from that provider/version's actual request examples. Record the base URL, credential header, static host header if required, operation paths, path/query parameters and any documented cursor paths. Keep credentials only in private .env under CRICBUZZ_API_KEY. Configure CRICBUZZ_CONTRACT_FILE with the reviewed manifest path.

The verified flag records an operator's documentation review, not successful authentication or live data verification. Do not set it merely to bypass validation. The transport can make an explicit raw smoke-check request after setup; a vendor JSON normalizer implementing services.matches.ProviderNormalizer is still required before live database ingestion.

No endpoint or subscription was guessed from a different listing. Transport protective defaults are not provider quotas. New providers should use a stable canonical ID/version and have sanitized fixtures and mapping tests before being enabled.
