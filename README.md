# CartMate

**Current product/engineering update (2026-10-14):** CartMate now supports short, mutually agreed outings for walks, study, fitness, food, conversation and errands—not only shopping. [Feature 003](context/feature-specs/003-activity-first-outings.md) records the activity contract, concrete meeting-point plan, no-expected-spend option, localized discovery and tested limits. The full backend/recovery suite passed 172/172 before the final correction that removed unsupported venue-safety ratings; its focused regression passed 1/1 afterward, while a new full run hit a Windows sandbox temp-directory permission error. Targeted activity browser passed 2/2; frontend build/typecheck and lint pass with the existing Vite chunk-size warning. The earlier full local browser run passed 42/42, but the latest run was 40/42 because the new server omitted the documented moderator fixture; its corrected rerun could not start due to a tool approval usage limit. Earlier isolated operator-pilot 16/16 and no-demo 4/4 results predate the final UI-only change. One-use WebSocket tickets are redacted from Uvicorn logs. No entered venue is independently certified as public/open. EC2, the domain-bound APK and human/physical gates H-01..H-06 remain unverified; do not invite real users yet. Older dated status text below is historical.

**Current product note (2026-10-14):** A [public-source comparison of WhatsApp, Meta, Meetup, Bumble and Timeleft patterns](PRODUCT_PATTERN_REVIEW_2026-10-14.md) informed a small trip-chat activity cue across tabs. No third-party app package was reverse-engineered. The closed Silesia pilot is not hosted or approved for real users; follow the EC2 staging runbook and complete H-01–H-06. The local debug APK exists but is tied to an older backend origin and must not be distributed as the AWS test build. Older status paragraphs below are historical.

**Latest independent closure (2026-10-13):** [MR3-01 is closed](qa/CODEX_MR2_VERIFICATION.md): 13 review regressions, five focused probes and frontend build/lint pass. Earlier MR2 findings stay closed. Java/SDK exist and an offline Android dry-run succeeds using the project's existing Build Tools 36.0.0 override; this is not a compiled APK. Next: private backend origin, native asset rebuild/sync, real APK build and physical testing. H-01–H-06 remain NOT RUN. This supersedes older open-fallback and missing-tool claims below.

**Current independent status (2026-10-13):** [Codex verification complete](qa/CODEX_MR2_VERIFICATION.md): original MR2-01/02 failures closed in the tested runtime. 158 backend/DR, 12 preflight, 16 operator browser cases, eight existing probes and build/lint pass; fresh offline dependency install + RT-17 also pass. One low-priority unsupported-runtime fallback cleanup remains (MR3-01), not a demonstrated supported-browser exploit. No hosted CI, APK or human/device sign-off.

**Historical independent status (2026-10-13):** [Codex retest 2](qa/CODEX_MVP_COMPLETION_RETEST_2.md) confirmed native destination and journey fixes, and identified MR2-01 and MR2-02, now remediated above.

CartMate helps adults find company for everyday activities and agree on a small outing. The intended first market is a closed, invite-only Katowice/GZM pilot. It is not a courier service and does not process payments or dispatch emergency responders.

**Release status (2026-10-13):** No live invitation is approved. Android APK preparation is the next approved milestone; actual phones, private HTTPS, witnessed age checks and protected off-host recovery remain strictly **NOT RUN** (H-01..H-06). Paid SMS/Render work is paused. Read the [current Gemini handoff](GEMINI_HANDOFF.md), [pilot spec](context/feature-specs/001-zero-cost-private-web-pilot.md) and [launch board](LAUNCH_READINESS.md) before inviting anyone.

## Codebase

The next release milestone is a [domain-bound private Android test APK](context/feature-specs/002-private-android-test-apk.md), with iPhone deferred. A local debug APK exists for an older origin; it does not establish a working AWS-connected handset build.

- `frontend/`: React 19, TypeScript, Vite 8 and Tailwind client.
- `backend/`: FastAPI, SQLite WAL persistence, WebSockets, SMS OTP and safety policy.
- `qa/`: isolated Playwright browser journeys.
- `ops/`: backup, restore and invite tools.
- `staging/` and `render.yaml`: parked paid Render/SMS rehearsal path; not the current no-cost pilot plan.
- `context/` and `AGENTS.md`: current architecture, decisions, progress and numbered implementation spec for the next coding agent.

## Local development only

Use a disposable SQLite database, not `backend/cartmate.db`. From `backend/`, install `requirements.txt` in a virtual environment and run `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000` with `CARTMATE_ENV=development`, `OTP_PROVIDER=console`, and `CARTMATE_DATABASE_PATH` pointing to your disposable file. From `frontend/`, run `npm ci` then `npm run dev`; the Vite client runs on `http://localhost:5280` and proxies `/api` and `/ws` to localhost:8000. Development demo accounts and codes must never be exposed on a shared host.

Before backend checks, install frontend dependencies (`npm ci` from `frontend/`): RT-17 requires Node and the local TypeScript package. Use the isolated database/environment settings in the [current retest](qa/CODEX_MVP_COMPLETION_RETEST_2.md), then run `python -m pytest -q` from `backend/`, `npm run build` and `npm run lint` from `frontend/`. Follow [QA instructions](qa/README.md) for browser tests. Legacy audit tests need credential-free shadow mode; the private pilot keeps Jev disabled. The release board records observed evidence and remaining gates.

Do not commit `.env` files, SQLite databases, OTPs, gateway keys, document data, Android signing keys or private backups. The root `.gitignore` excludes common local artifacts, but review every first commit and hosted secret separately.
