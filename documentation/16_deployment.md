# Deployment — current status

The user-selected target is Streamlit Community Cloud, repository purans07/Cricbuzz-LiveStats-, branch main, entrypoint cloud_app.py, Python 3.13, no sample-demo secrets. Source is uploaded. Linux Docker build, healthy startup, all six pages and persistence after restart passed. The public sample at https://cricbuzz-livestats-web.streamlit.app/ passed hosted acceptance; see cloud_verification.json. See [launch settings](community_cloud_deployment.md) and [mode comparison](live_refresh_and_demo.md).

The remaining sections retain deployment options and earlier preparation context; current status above supersedes older pending-build statements.

# Phase 16 — Deployment preparation

This phase compares the requested hosts and supplies a portable, read-only sample deployment. **No site has been published, registry image pushed, cloud account changed or paid resource created.** Python startup/UI checks pass; an actual Linux Docker build, healthy container, six-page rendering and restart persistence have now passed. Public Streamlit URL acceptance remains pending.

## Concepts and chosen design before implementation

Deployment changes the execution environment: dependencies must install on the target OS, a process must bind the host's expected interface/port, startup must find its data, secrets must remain private and a restart must have a defined storage policy. A healthy HTTP endpoint does not prove database integrity, API authentication or every page's behavior.

The current app supports local SQLite and a trusted local-operator access mode. It does not have public administrative authentication, a shared multi-instance writer/coordinator but now includes verified PostgreSQL/MySQL support. A public deployment therefore defaults to sample data and public_readonly: no CRUD writes, custom SQL or provider refresh writes. The complete local application remains available through main.py for trusted use.

Recommended first target: **Docker packaging for a read-only synthetic demo**, with an optional credential-free Streamlit Community Cloud route. The image excludes working databases and private configuration, and generates only a missing reviewed sample database at startup. Persistent live administration is a separate deployment decision, not an automatic consequence of uploading this app.

## Hosting comparison

| Option | Suitable use for this project | Storage/access considerations | Status |
| --- | --- | --- | --- |
| Streamlit Community Cloud | Simple sample portfolio demonstration from a reviewed repository | Use cloud_app.py; the demo can regenerate its sample. Do not rely on a mutable local SQLite file as authoritative hosted storage | Steps documented; not published |
| Render | Docker web service; sample demo or single-instance storage-aware setup | Default filesystem is ephemeral; a persistent disk requires an eligible paid service. Keep public demo read-only | Steps documented; no resource created |
| Railway | Container service with a mounted volume where persistence is needed | Explicit volume and target port; one instance for SQLite; account/usage costs need review | Steps documented; no resource created |
| Azure | Managed container/App Service deployment for an organization | Configure container port, storage and access using the chosen App Service configuration; do not assume container filesystem persistence | Steps documented; not provisioned |
| AWS | ECS/EC2 container deployment with controlled networking | Match load balancer/WebSocket requirements and storage to the app. App Runner's filesystem is ephemeral and is not persistent SQLite storage | Architecture steps documented; not provisioned |
| Docker | Reusable local/VM packaging and a reproducible runtime input set | Non-root runtime, explicit files, local-only published port in Compose and a named sample volume | Image build, health, six pages and restart verified locally |

These are project-specific recommendations, not promises of current pricing, free quotas or an already-provisioned service. Current primary references: [Streamlit Community Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app), [Streamlit repository organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization), [Render disks](https://render.com/docs/disks), [Railway volumes](https://docs.railway.com/volumes), [Azure container configuration](https://learn.microsoft.com/en-us/azure/app-service/configure-custom-container), [AWS App Runner storage model](https://docs.aws.amazon.com/apprunner/latest/dg/develop.html) and [AWS ALB WebSocket listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html). These documents were consulted during preparation; hosted capabilities/billing should be rechecked when creating resources.

## Deployment artifacts

| File | Responsibility |
| --- | --- |
| Dockerfile | Python 3.13 image, pinned installed package set, explicit application copies, non-root user, health check and public-demo startup |
| .dockerignore | Deny-by-default build context with application allowlist; exclude keys, working databases, local manifest and caches |
| compose.yaml | Local Docker demo on 127.0.0.1:8502 with a named sample volume |
| cloud_app.py | Public sample/read-only Streamlit entry; sets effective process settings before the normal app navigation |
| deployment/public_demo.py | Validate demo policy, initialize only a missing sample target, then validate it read-only |
| tests/test_deployment.py | Startup policy, idempotence, preservation, safe failure and actual readonly route tests |

The base tag python:3.13-slim is mutable; requirements-lock.txt fixes Python package versions, not the image digest, Python patch version, OS libraries or availability of Linux wheels. The lock comes from the checked local environment and also includes development tools. After a successful target build, record/pin the image digest and test target dependencies rather than claiming full bit-for-bit reproducibility now.

Docker copies application directories, reviewed SQL/sample input, documentation and theme, rather than COPY . . It does not copy .env, .streamlit/secrets.toml, the managed Git/workspace metadata, original Word references, raw captures or runtime databases. The existing operator-local provider manifest is excluded. Do not add secrets through build arguments or commit private files to a deployment repository. The sample demo requires no API key.

## Public startup and persistence behavior

`prepare_public_demo` reads an explicit environment mapping rather than loading a private .env. Defaults are sample, public_readonly and a separate public-demo.db. Unsafe live/local modes are rejected **before** any file creation. A missing target is initialized with the reviewed fictional seed using startup-only local initialization permission, then opened read-only for all pages. An existing file is validated and never reseeded, overwritten or silently migrated. Atomic initializer behavior handles a concurrent creation winner by validating its existing target.

cloud_app.py installs those effective mode/path/access/timezone values into process environment before running normal main.py navigation. They therefore override accidental private-file defaults during subsequent page settings loads. There are no UI permission-changing controls. A startup error shows a safe message and stops; it does not continue into a partially configured writable application.

Compose uses a dedicated named demo-data volume. Do not mount the working data/runtime folder or a private .env into the sample image. For a host bind mount, the runtime user is UID 10001 and needs appropriate ownership/access; do not solve permission problems by making every file world-writable. A new named volume should receive the image directory's non-root metadata, and the named volume retained 72 sample matches across the verified restart.

Public pages can select Saved provider, but the packaged sample image contains no working live.db, so that target is unavailable unless separately provisioned. Do not mount private provider databases merely to make that selector nonempty. Public readonly is an application write policy, not OS-level filesystem immutability: startup needs writable space to create the sample.

## Selected path: local Docker demonstration

First start the installed Docker engine and verify it responds. The engine was unavailable during this phase; no background system service or application was started automatically.

From the project root:

```sh
docker info
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

Open [the container demo](http://127.0.0.1:8502). Port 8502 avoids colliding with the existing trusted local dashboard at 8501. The container listens on 0.0.0.0:8501 internally; Compose publishes only to the host loopback address. A plain public internet listener is not created by this configuration.

Verify the HTTP health endpoint:

```sh
curl --fail http://127.0.0.1:8502/_stcore/health
docker compose logs --tail 50
```

Then check all six pages, SAMPLE labels, chart/SQL results, disabled API refreshes, absent CRUD forms/custom SQL and readonly Settings. Restart the service and verify counts persist rather than resetting unexpectedly. The health endpoint is process liveness, not a database/API acceptance test. Streamlit documents this health-check approach in its [Docker tutorial](https://docs.streamlit.io/deploy/tutorials/docker).

Stop the demo without deleting its volume:

```sh
docker compose down
```

No destructive volume-reset command is part of ordinary startup/recovery. To troubleshoot installation, inspect build logs and verify Python/package availability for the target platform; do not silently unpin dependencies or claim the image was tested if it did not build.

## Optional Streamlit Community Cloud sample demo

1. Prepare a reviewed repository containing the application, cloud_app.py, deployment helper, SQL, sample seed, theme and documentation. The existing local project has uncommitted work; do not assume it is already in a remote repository.
2. Exclude private keys, runtime/raw files and local contracts. Review exactly which files will be published; this phase does not commit or push them.
3. In Community Cloud choose the intended repository/branch and **cloud_app.py** as the entry point, not main.py.
4. Select a Python version compatible with the checked Python 3.13 dependency set where supported, and verify the build log. Do not choose an older interpreter and assume the locked packages work.
5. No API secret is needed for the fictional demo. Use the safe startup defaults; do not set APP_ACCESS_MODE=local or DATA_MODE=live.
6. After deployment, run the readonly page acceptance checks above. Reboots may recreate disposable sample state; it must not become an authoritative mutable data store.

The application currently uses private .env/process environment for provider access, not an automatic st.secrets bridge. Do not paste a key into a hosting secrets panel and claim this loader consumes it unless that integration is explicitly added and tested. This sample deployment avoids that dependency entirely.

## Render and Railway steps

For a **sample** container deployment: connect a reviewed repository or approved built image; use Dockerfile, cloud_app.py, readonly sample settings and internal port 8501. Configure the platform's expected port consistently with the fixed container command (for example PORT=8501 where that platform uses it). Use /_stcore/health as the HTTP health endpoint and verify browser/WebSocket operation before acceptance.

Render's default filesystem is ephemeral; its persistent disk option is available on eligible paid services. Railway provides explicit volumes. For this disposable sample, regenerating a missing reviewed seed is acceptable; for lasting records, mount the chosen persistent storage at /app/data/runtime, use one instance, arrange backups and validate UID permissions. Review current billing before creating a service/disk. No service or paid storage was created here.

A public writable live deployment is not enabled by changing the image's environment: cloud_app.py rejects it. Use main.py only in a trusted/restricted deployment with an agreed access model, persistence and backup design. Do not globally set APP_ACCESS_MODE=local on a public demo as a substitute for authentication.

## Azure and AWS steps

Azure: build and validate the image, publish it only to an approved registry, create the intended managed container/App Service resource, set its container target port to 8501 and verify WebSocket behavior. Choose storage using the current App Service container configuration (including enabled persistent storage or an explicit supported mount when required), set readonly sample policy, and run acceptance checks. Registry, identity, TLS/domain, storage and billing changes remain operator actions, not completed work.

AWS: a controlled EC2 Docker host or ECS service behind an Application Load Balancer is an architectural option. Publish an approved image, configure the task/container port 8501, scope inbound traffic to the intended load balancer/proxy, provide HTTPS and verify WebSocket sessions. Choose storage appropriate to SQLite and single-instance operation or implement/test a different database backend first. An ALB supports WebSocket upgrades; this does not prove every AWS compute/storage configuration suits the app. Do not place authoritative SQLite state on App Runner's ephemeral filesystem.

These Azure/AWS paths are guidance rather than ready-to-apply infrastructure templates. Region, account, identity, network, domain and cost decisions were not supplied, so they are not invented or provisioned.

## Verification and remaining acceptance

Six new automated cases cover idempotent sample bootstrap/readonly enforcement, rejection of unsafe modes before creation, preservation of an incompatible existing database, actual public entry point/Home/CRUD/Analytics rendering and safe startup refusal. Full suite: **519 tests passed**; lint/format/whitespace checks pass. `docker compose config --quiet` passes without an engine.

[The preparation report](16_deployment_result.json) distinguishes automated startup acceptance from unavailable Docker engine/build/run and unperformed hosted acceptance. Neither a successful local Python test nor a valid Compose document proves a Linux container build, volume mount, hosted networking or production deployment. Working sample/live files and private configuration were not changed or copied into an image. No site was published or API request made.

## Phase completion

**Completed:** comparison of all six requested options, chosen Docker/readonly sample design, startup helper/entry point, explicit-copy image and build-context controls, Compose configuration, deployment/recovery/acceptance steps and six automated startup cases.

**Pending runtime acceptance:** start Docker, build/run the image and verify its health/volume/browser behavior. Hosted publication remains unperformed and requires a selected account/repository/host; no subscription is needed merely to prepare this package.

**Concepts learned:** image versus container, pinned dependencies versus reproducible images, process/port health, bootstrap versus migration, ephemeral versus persistent data, public demo versus trusted administration and preparation versus actual deployment.

**Next phase preview:** Phase 17 — Documentation will finish the README, installation/folder/API/database guidance, screenshots section and future improvements while preserving these deployment limitations. Phase 16's teaching/preparation scope is complete; actual container/host acceptance is explicitly pending.
