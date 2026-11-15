# Scope for Claude: friends pilot hardening

Prepared 2026-11-15. Start from the actual current branch and source, not a remembered test count.

**Objective:** Prepare a closed browser trial for at least three trusted adults in Silesia on the single approved staging host. Prove one complete pod journey at one personally visited public venue, plus a separate two person voice call. Android and the later roughly 100 person/store release are separate gates.

**Build approach:** Tracer Bullet, preserving the existing stack and proving each changed behavior through storage, API and UI where applicable.

**Workflow:** Beta, with targeted regression tests and observed acceptance evidence. These workflow names do not represent release approval.

This file extends [the existing feature scope](scope.md), whose features 1 through 13 describe earlier implementation. Features 14 through 25 below cover the next hardening work. They are planned, not verified fixes. The supplied audit is a set of hypotheses to reproduce. If a claim is false or already fixed, record the evidence and omit the proposed code change.

## Starting point and working boundaries

The local HEAD inspected while writing this scope is `ba030ce`, the PR #1 merge commit. The current handoff reports 254 Python tests, 50 development browser tests, 4 no-demo tests, 16 operator tests, 5 CI probes, and a Docker build/smoke pass on hosted CI. Those checks were not rerun for this scope. The separate 6 pod/voice browser cases overlap the development suite; do not add them to a distinct test total. Nine local diagnostic probes and five hosted probes are different verification sets.

PR #1 already addresses the cooldown dependent navigation assertion, timezone lookup failing open, and the nine falsely verified venue seeds. Preserve those fixes. Its successful workflow runs do not prove execution continues correctly after a failed check.

Read `AGENTS.md`, the six context files in their prescribed order, current numbered feature specs, `LAUNCH_READINESS.md`, and the current `GEMINI_HANDOFF.md` before implementation. Read `docs/CODEX-NAVIGATION-GUIDE.md` if present; it was absent when this scope was prepared. Use current source to resolve stale historical statements. Record any new design in the repository's spec workflow before a change that needs a product or architecture decision.

At preparation, `GEMINI_HANDOFF.md`, `LAUNCH_READINESS.md`, and `context/progress-tracker.md` already had uncommitted edits. Preserve them and coordinate one writer for shared files. Inspect the worktree again before starting; do not reset or blindly pull over other work.

Set a unique disposable `CARTMATE_DATABASE_PATH` before importing any backend module, including one line probes. Never run migrations or tests against `backend/cartmate.db`, the pilot database, or a real backup. The local database was previously changed by an accidental import and cannot be reconstructed from a known prior copy. Preserve it and the saved virtual environment; do not use either database contents or test accounts as a pilot seed.

Founder decisions to preserve:

1. Friends first, at least three trusted adults. About 100 participants and store distribution are later aspirations, not authorization to launch now.
2. The founder and one backup are human moderators. Open voice hours do not mean continuous monitoring.
3. Staging voice is open all day. Production currently enforces 18:00 to 23:00 Warsaw time; revisit that policy before production release, not during this slice.
4. A moderator must actually visit a venue before recording verification. Do not fabricate a visit, timestamp or operator identity.
5. AI monitoring is deferred. Do not build it in the friends slice.

Use truthful operator admission and witnessed adult checks for live staging. Demo tokens, mock identities, captured OTP adapters and age bypasses belong only in isolated tests. Keep block, report, revocation, region and age checks server enforced; keep direct 112 guidance.

This scope is a work plan, not authorization to push, merge, publish, change repository visibility or branch rules, or invite public users. Follow the existing single EC2 authorization and cost check in `ops/EC2_STAGING_RUNBOOK.md`; no extra paid services, paid SMS or identity document collection is included.

## At a glance

| # | Feature | Phase | Status |
|---|---|---|---|
| 14 | Durable pod expiry | Friends software | implemented locally, uncommitted |
| 15 | Proxy headers and credential safe logs | Friends software | planned |
| 16 | Explicit venue verification and pilot readiness | Friends software | designed and accepted, not built |
| 17 | Truthful voice availability | Friends software | implemented locally, uncommitted |
| 18 | CI failure behavior and test isolation | Friends software | planned |
| 19 | Hosted friends rehearsal | Friends runtime | planned |
| 20 | Android audio and packaging | Later Android | planned |
| 21 | Voice network resilience and relay policy | Later expansion | planned |
| 22 | Explicit database startup and durable settings | Later expansion | planned |
| 23 | Repository governance | Later expansion | planned |
| 24 | Focused maintainability improvements | Later cleanup | planned |
| 25 | Expansion and store release decision | Later expansion | planned |

## Friends software, complete before live rehearsal

### 14. Durable pod expiry (planned)

Ensure an expired forming pod stays cancelled after the request ends. Inspection found sweep updates in `list_pods` and `join_pod`; prove their transaction behavior through a fresh connection before choosing the fix.

**Done when:** listing persists expired cancellations; rejected and duplicate joins do not discard required sweep changes; a fresh connection and process restart observe cancellation; expired pods cannot accept members or chat; active pods and capacity constraints retain their behavior. Cover successful, early return and exception paths without partially committing an unrelated join.

- [x] Reproduce and implement: `/develop durable pod expiry`

**Finding disposition (2026-11-15): confirmed, lower severity than assumed.** The sweep was lost unless a join succeeded, but the existing 60-second background sweep bounded the wrong status to about a minute and an expired pod could not be joined meanwhile. Fixed, including the single-pod read path found in review; 9 tests cover it. Evidence is in `context/progress-tracker.md`.

Code area: `backend/storage.py`, pod API and migration tests.

### 15. Proxy headers and credential safe logs (planned, needs a decision)

Define an explicit proxy configuration for the existing Caddy deployment. Confirm actual logging behavior first; missing redaction code does not itself prove an enabled access log is leaking tickets.

**Done when:** deployed response checks prove the chosen HTTPS, CSP, framing and content type policies; maps, assets, API, WebSockets and voice still work; synthetic ticket and credential sentinels are absent from all enabled application/proxy access and error logs. Avoid an overly broad CSP or an untested policy that breaks WebRTC or MapLibre. Validate the configuration in the deployment image.

- [ ] Capture policy and implementation plan: `/architect pilot proxy hardening`

Code area: `docker-compose.yml`, existing logging configuration, frontend asset and connection destinations.

### 16. Explicit venue verification and pilot readiness (planned, needs a decision)

Provide the smallest usable moderator flow to add a place and explicitly record a real visit, including for existing seed rows. Place creation alone must not imply an inspection. Keep the nine seeds unverified.

**Done when:** omission of verification leaves a place unverified; authorized explicit attestation records actor and visit time; ordinary or inactive users cannot verify; a moderator can complete the flow without raw SQL; unverified places cannot be used to create pods; upgrade and reseed preserve legitimate visits. Empty venue inventory is visible in the UI and in an operational pilot check that prevents a pod pilot being declared ready.

Decide whether `/api/ready` represents infrastructure health or complete pilot readiness. Preserve bootstrap access and liveness when the inventory is empty. A separate explicit pilot readiness result is acceptable if the deployment go/no-go check requires it.

- [x] Capture verification and readiness contract: `/architect explicit venue verification`

**Design (2026-11-15):** `context/feature-specs/004-explicit-venue-verification.md`. Not built. It adds one finding: the app has no screen for scheduling a pod. Revision 2 separates closing a venue from withdrawing a visit and keeps earlier verification for audit. The founder accepted its seven decisions on 2026-11-15.

Code area: `backend/storage.py:create_third_place`, `backend/main.py` pod place and readiness routes, moderator UI, migrations after 0016 if needed. Do not rewrite applied migrations.

### 17. Truthful voice availability (planned)

Expose the effective voice policy from the server so staging does not advertise an enforced evening window.

**Done when:** the status response and all four UI languages distinguish unrestricted staging, an enforced open window, a closed window, and configuration failure; production and explicit enforcement still fail closed on missing timezone data; cooldown and daily limits remain independent. Test Warsaw boundary times and daylight saving behavior. Do not imply all day moderator coverage.

- [x] Implement and verify: `/develop truthful voice availability`

**Result (2026-11-15):** implemented locally, uncommitted. 24 backend tests and 9 browser cases (desktop and mobile, four languages) pass. Evidence is in `context/progress-tracker.md`.

Code area: `backend/voice_manager.py`, voice status route, `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/components/VoiceCallHUD.tsx`.

### 18. CI failure behavior and test isolation (planned, needs a decision)

Prove the workflow's failure paths and remove shared account state as a hidden browser test dependency. Keep the legitimate heading assertion from PR #1.

**Done when:** a deliberate check failure leaves the overall run red while eligible independent checks still execute; dependency install failure skips dependent work; a failed frontend build skips browser tests; a failed image build skips its smoke test. Browser tests work alone and in the full suite, including connect and cooldown behavior. Remove failure injection before merge and record the diagnostic run or equivalent test evidence.

Prefer the smallest workflow adjustment supported by evidence. Separate jobs may help, but neither blanket fail-fast nor always-running dependent steps satisfies this requirement. Do not deliberately fail `main`.

- [ ] Design isolated failure verification and fixtures: `/architect trustworthy CI failure behavior`

Code area: `.github/workflows/ci.yml`, `qa/playwright*.config.ts`, browser fixtures and diagnostic probes.

## Friends runtime, after features 14 through 18

### 19. Hosted friends rehearsal (planned, requires human participation)

Use the existing EC2 runbook and one host to prove the closed browser experience. A Docker smoke test is not this rehearsal.

**Done when:** the chosen commit runs over the actual HTTPS origin; one real visited venue is explicitly verified; at least three admitted adults form a pod and exchange chat; two real devices exchange audible voice on distinct networks with a forced relay test and observed relay candidates; cancellation, block, report, revocation, restart and protected restore are exercised; moderators know their coverage and escalation responsibilities; each H-01 through H-06 gate has dated evidence and an owner.

Record browser/device versions, network conditions, failures and participant feedback. Exercise a restrictive NAT/network scenario where available; do not infer it from two devices on one Wi-Fi network. Demonstrate an encrypted backup restored into a separate scratch database, never over live data. Human identity, venue visits and usability cannot be certified by an agent.

- [ ] Prepare and execute the approved runbook rehearsal with the founder.

Gate: no real trial admission until the required software fixes and operational preflight pass. Do not describe the friends pilot as ready until the applicable human/device gates are observed.

## Later work, not a reason to delay a bounded browser pilot unless a reproduced defect affects it

### 20. Android audio and packaging (planned, needs a decision)

Verify the existing Capacitor permission behavior before adding native bridge code. Avoid replacing its WebChromeClient blindly.

**Done when:** microphone grant, denial, revocation, cancellation and audio routing work on an actual target Android handset; merged manifest permissions and backup policy are intentional; native origin checks hold; a build matches the private backend; CI builds Android. Release signing and key custody have an approved plan before any store package is produced.

- [ ] Capture the native audio and release plan: `/architect Android voice packaging`

Code area: `frontend/android/`, `scripts/build_android_apk.ps1`, native routing helpers.

### 21. Voice network resilience and relay policy (planned, needs a decision)

Decide the supported connection modes and failure behavior from real device and relay evidence.

**Done when:** disconnect/reconnect and ICE recovery are bounded, preserve block/revocation behavior, and cannot revive ended calls; direct versus relayed status follows actual connection statistics; unavailable relay configuration produces an honest result; any required TURN TLS listener has valid certificate renewal and successful relay tests.

Do not equate a non-TLS TURN listener with unencrypted WebRTC audio. Evaluate signaling/relay transport, media encryption and direct peer address exposure separately. Do not silently remove working STUN paths without deciding the supported direct/relay policy.

- [ ] Capture supported networks and privacy policy: `/architect voice transport resilience`

Code area: `backend/voice_manager.py`, `frontend/src/components/VoiceCallHUD.tsx`, `docker-compose.yml`.

### 22. Explicit database startup and durable settings (planned, needs a decision)

Remove accidental database mutation on ordinary imports and reproduce the reported settings persistence and authorization gaps.

**Done when:** imports create or migrate no default database; explicit startup performs migrations with a clear configured path; settings changes survive reload and restart; moderator checks share the same enforced authority; invalid deployed authentication configuration fails safely. Preserve operator admission on staging while proving production cannot authenticate through console OTP.

Separate startup lifecycle and settings persistence into small implementation slices. Promote any reproduced live security defect into the friends phase rather than waiting for expansion.

- [ ] Capture lifecycle and persistence boundaries: `/architect explicit storage lifecycle`

Code area: `backend/storage.py`, `backend/database.py`, FastAPI lifespan, settings routes, `backend/config.py`.

### 23. Repository governance (planned, needs a founder decision)

Prepare branch protection and ownership choices without changing third party settings automatically.

**Done when:** the founder decides repository visibility/licensing and source disclosure; an approved protection policy requires review and the actual CI check; bypass permissions are deliberate; sensitive tracked data is handled according to evidence. Public visibility alone is not a vulnerability or a reason to claim code was compromised.

- [ ] Propose repository policy for approval: `/architect repository governance`

### 24. Focused maintainability improvements (planned, needs a decision)

Reduce risk in measured increments, preserving behavior and test evidence.

**Done when:** agreed modules are extracted behind stable contracts, measured N+1 queries are reduced, TypeScript strictness is increased without blanket suppressions, locale duplication is consolidated, and noncritical bundles load when needed. Separate frontend contract tests from Python only when equivalent trust boundary coverage remains. Reconcile stale documentation without deleting another agent's artifacts, backups or untracked work.

- [ ] Choose bounded refactor slices and measurements: `/architect CartMate maintainability`

Code area: `backend/main.py`, `backend/storage.py`, frontend TypeScript config and components, QA and context documents.

### 25. Expansion and store release decision (planned, needs a founder decision)

Use the friends trial to decide whether a larger cohort is justified before implementing the next launch.

**Done when:** the founder reviews actual completion, comfort, repeat interest and moderation effort; audience, staffed hours, privacy/retention, account deletion, age assurance, device/platform support, hosting capacity and store obligations have an approved plan with acceptance criteria. Any AI monitoring proposal states purpose, data access, consent, costs and human escalation before implementation.

- [ ] Scope the next cohort from pilot evidence: `/architect controlled expansion`

## Delivery and evidence expected from Claude

Start with feature 14 and work in small reviewable slices. Before a fix, record a reproduction or a precise code finding and add a failing regression where practical. Keep a short finding disposition: confirmed, already fixed, not reproduced, or awaiting human evidence. Do not mechanically implement every suggestion in the audit.

For each completed slice, record changed files, relevant commands and actual results, environment and commit, unresolved risks, and the next gate. Run the applicable backend, frontend and browser checks on disposable data. Use dependency audits before committing as required by the project instructions. Broaden testing once the combined friends software change is ready; do not carry old counts forward or hide skips.

After coordination with the current documentation owner, update the progress tracker, active handoff and launch readiness with observed facts. Keep a concrete review diff; commits, pushes, PR creation, merges, infrastructure changes and public distribution follow the current user authorization boundaries.

Completion of software work means a reviewable change set with passing applicable checks. Completion of the friends pilot gate additionally requires feature 19 evidence. This scope does not confer launch approval, and the later phases remain deferred until selected.
