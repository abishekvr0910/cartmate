# CartMate — research, product design, and executable handoff to Gemini

**Prepared:** 2026-10-14. **Recipient:** Gemini. **Scope:** finish the *closed, supervised, adult-only Silesia pilot*, not a public Poland launch. This document is a research-backed execution brief, **not** a release sign-off or a claim that the remaining work has been done.

## Read this first: authority and evidence

1. Follow `AGENTS.md` and read the six `context/` files in its prescribed order, then `context/feature-specs/001-zero-cost-private-web-pilot.md`, `002-private-android-test-apk.md`, `003-activity-first-outings.md`, and the top of `LAUNCH_READINESS.md`. For the current cloud choice, **`ops/EC2_STAGING_RUNBOOK.md` supersedes Lightsail, Render, and Tailscale instructions in older handoffs**. `PRODUCT_PATTERN_REVIEW_2026-10-14.md` is the preceding public-pattern review. The open-source architecture document is an *idea catalog*, not verified source extraction or a license to copy code.
2. Verify the current source and rerun tests before editing or repeating any count. Existing `GEMINI_HANDOFF.md` and progress files contain historical, contradictory paragraphs (including old zero-cost hosting and “no APK built” snapshots); do not follow those over dated top-level decisions. Correct or archive stale text as part of handback.
3. One writer owns shared files. Preserve `backend/cartmate.db`, any actual pilot database, `CODEX_WORK_DIRECTORY.md`, secrets, signing material, and other agents' changes. Tests use fresh disposable SQLite databases. Do not upload the dirty worktree wholesale, provision AWS, incur new paid services, invite users, or distribute an APK without the founder's scoped go-ahead and the relevant gates.

| Current proposition | What is actually evidenced locally | What is **not** evidenced |
| --- | --- | --- |
| Product | React/FastAPI/SQLite/WebSocket two-person meetup flow; activity categories `study`, `fitness`, `walk`, `food`, `social`, and legacy `quick` shown as errands; mutually accepted plans, chat, check-in/PIN, cancellation, reporting/blocking, 50/50 ledger, double-opt-in follow-up. | That people find it intuitive, form durable connections, or feel less lonely. |
| Security/safety | Local auth/authorization, adult gate, moderation, revocation, and recovery regressions exist. SOS is disabled for SMS in the approved pilot and falls back to direct **voice** dialing of 112. | An independent production penetration test, guaranteed venue safety, or an emergency-response service. |
| Verification | The 172/172 backend+recovery run predates the final rendezvous wording edit; the focused post-edit test passed 1/1. Earlier full browser run was 42/42; a later run was 40/42 with the documented moderator fixture missing; a corrected rerun did not execute. Targeted activity journey 2/2 and frontend build/lint passed. Earlier isolated operator 16/16 and no-demo 4/4 predate the final UI edit. | A current clean full-suite green result; physical Android/iPhone, real screen-reader, live network, or cloud verification. Passing tests is not “100% coverage.” |
| Distribution | An Android debug APK exists locally, tied to a previous backend origin. `git` has no first commit or remote in this checkout. | Shareable production-domain APK, private GitHub source, EC2 instance/domain/TLS, off-host restore, or invited-user deployment. |
| Launch | EC2 single-host staging is the founder's current choice; H-01–H-06 are written down. | **H-01–H-06 remain NOT RUN**. No public or nationwide launch approval exists. |

## Research synthesis: what to borrow and what not to claim

The [WHO Commission on Social Connection report](https://www.who.int/publications/i/item/978240112360) establishes loneliness and social isolation as important, widespread problems. It does **not** show that CartMate, gamification, or any particular app reduces loneliness. Treat “company for ordinary life” as a hypothesis to test with users, not a health outcome claim. CartMate should not market itself as therapy or crisis support.

| Primary source and observed pattern | CartMate inference / proposed experiment | Boundary |
| --- | --- | --- |
| [Bumble For Friends Plans](https://bumble.com/the-buzz/bumble-for-friends-plans) exposes activity, time, city, ask-to-join, host review, then group chat. | Keep discovery **activity-first** and make request → accepted → mutually confirmed visibly different states. Test whether the five new activities let participants describe a meetup naturally. | Bumble's product page is not evidence of CartMate demand or safety. Do not copy its assets or swiping mechanics. |
| [WhatsApp group events](https://about.fb.com/news/2024/05/events-in-whatsapp-communities/) and [event reminders](https://about.fb.com/news/2026/01/whatsapp-group-chats-member-tags-text-stickers-event-reminders/) keep a plan discoverable within a chat and optionally remind invitees. | One compact, accessible trip card should show who/what/when/where/cost/status and the next action. If users ask for it, test **one optional** pre-meet reminder with cancellation-aware delivery. | No read receipts, default push, urgency streaks, or “WhatsApp-level security” claim. Current trip-tab cue is session-only, not push or persistent unread state. |
| The [Center for Humane Technology's product-design framework](https://www.humanetech.com/humane-product-design), from the organization behind *The Social Dilemma*, asks builders to account for human psychology and incentives. | Treat a successful **offline meeting with agency to leave** as the intended outcome. Review every notification, feed and gamified element for its real-world benefit before adding it. | This is a design framework, not an experiment proving that CartMate helps users. Do not turn “anti-loneliness” into a streak or shame mechanism. |
| [Timeleft's own safety explanation](https://www.timeleft.com/blog/safety-starts-before-the-dinner/) emphasizes public venues, controlled sharing, and reporting. | Test whether a participant can identify the meeting point, leave independently, find block/report, and understand what CartMate has *not* verified. | This is a vendor claim, not independent proof; CartMate has **not** vetted its venues. A typed `meeting_point` or OpenStreetMap tag is not proof a place is open, accessible, staffed, or safe. |
| [EDPB Statement 1/2025 on age assurance](https://www.edpb.europa.eu/documents/statement/statement-12025-on-age-assurance_en) and the [Polish government's mDowód QR guidance](https://www.gov.pl/web/cyfryzacja/kod-qr--skuteczna-metoda-weryfikacji-mdowodu) favor appropriate, data-minimizing age checks; Poland's ministry describes a live QR/official verifier flow. | Keep CartMate's **product-policy** 18+ gate fail-closed; use only a correctly witnessed supported method, record the minimum attestation metadata, and do not retain ID images or numbers. | Merely seeing mObywatel on a screen is not a verified QR scan. Do **not** state that Polish law universally mandates 18+ for meetup apps. Obtain a qualified Polish privacy/legal review before public expansion. |
| [European Commission GDPR principles](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/principles-gdpr_en) and [DSA FAQ](https://digital-strategy.ec.europa.eu/en/faqs/digital-services-act-questions-and-answers) inform minimization, retention, transparency and notice/moderation design. | Prepare a real data inventory, retention/deletion procedure, privacy notice, incident workflow, and an applicability assessment for DSA/GDPR obligations. | Neither code tests nor this brief certify legal compliance; exact obligations depend on the service and operation. |
| [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) requires a **complete-process** accessibility assessment, including reflow, keyboard/focus, target size, accessible authentication, and status announcements. | Audit the entire auth → discovery → plan → chat → cancel/report/SOS journey on actual devices, not just screenshots or one modal. | Browser emulation and a 320px overflow assertion are useful regressions but not WCAG 2.2 AA conformance evidence. WCAG 2.2's 2.5.8 AA minimum is 24 CSS px with exceptions, **not** a blanket 44 px rule. |
| [SQLite WAL](https://www.sqlite.org/wal.html) permits concurrent readers but one writer and requires local filesystem semantics; its [online backup API](https://www.sqlite.org/backup.html) supports consistent snapshots. [AWS S3 guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html) and [EC2 IAM roles](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) support private off-host custody without static access keys. | One EC2 worker plus a persistent encrypted disk is a bounded pilot shape. Rehearse backup → off-instance copy → scratch restore → authorization checks before inviting people. | A successful local backup script is not proof of S3 custody or recovery. Do not add a second worker/instance to the current SQLite + in-process WebSocket design. |

The [AWS Pricing Calculator](https://calculator.aws/) and [AWS Budgets documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) are the cost sources for provisioning. A budget alert is **not** a hard spend cap. Recheck prices and free-tier eligibility in the founder's account; do not assume EC2, public IPv4, EBS, S3, snapshots, or egress are free. For independent technical review, use the current [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) and [MASVS](https://mas.owasp.org/MASVS/) as checklists, not as badges earned by running tests.

**Open-source decision:** The 11-project catalog in `OPEN_SOURCE_ARCHITECTURE_STRIP_CODEX.md` is not a mandate to import code. Current pilot needs do **not** justify a new map tile dependency, live Overpass venue queries, PostgreSQL booking engine, temperature reputation score, or Synapse/Discourse deployment. OSM-derived POIs cannot be labeled “verified safe.” If a later task does require upstream code, first inspect the exact current source/license and record provenance, obligations, test case, and why the existing implementation failed. The pilot's two-person plan, ledger, block/report, and socket revocation already have local code; improve only on a reproduced defect.

## Product design document: the smallest coherent experience

**User and job:** An adult in Silesia has an ordinary activity they would do alone—study, walk, gym, food, errand, or an unpressured conversation—and would welcome another person, but does not want a date, courier, open-ended group chat, surprise expense, or pressure to stay. The first cohort is the founder and a trusted adult friend, then a *small staffed invite-only* cohort only after evidence and founder authorization.

**Core loop:** Choose an activity and bounded time → write a specific, mutually visible plan and expected cost → another adult asks to join → host accepts → both explicitly accept the plan → use private trip chat for coordination → meet at the chosen public-facing point and verify the PIN → end, cancel without guilt, report/block if needed → private double-opt-in to meet again. A request is **not** an acceptance, an accepted request is **not** a mutually approved plan, and a PIN is **not** a safety certificate.

**Pilot experience contract:**

- One action-led home state: “What would you like company for?” with the six understandable activities. The feed/map is a way to find an actionable outing, not an engagement destination. No lonely-person labeling or clinical promise.
- A plan card always makes activity, local time/date, duration, specific meeting point, access/cost expectations, host/companion commitment, and present state legible. `no_expected_spend` shows zero estimate; 50/50 applies only when those terms are chosen. If the typed point is unverified, say so plainly and prompt people to confirm it themselves.
- “Pending,” “accepted—confirm the plan,” “ready,” “cancelled,” and “completed” have different copy and next actions in PL/EN/UK/RU. Do not celebrate an outing at request time. Changes require mutual acceptance again.
- Exit and safety are in context: low-guilt cancellation, immediate other-device state change, block/report at discomfort, accessible direct `tel:112` fallback. Never imply CartMate, Jev, or an SMS gateway has dispatched emergency services.
- Jev remains advisory and optional: no auth, age, moderation, venue certification, SOS, PIN, or money decisions delegated to it; redact before external calls, and keep it disabled for the agreed hosted pilot.

**Pilot non-goals:** public Poland discovery; minors; unsupervised cohort; dating claims; “loneliness cured” metrics; streaks/leaderboards/infinite scroll; ubiquitous live location; automatic venue “safety” scores; paid carrier/SOS integration; native iOS build; multi-region/multi-instance scale. Revisit only after users and operators demonstrate demand and safety.

**How to learn without fooling ourselves:** Conduct a small number of uncoached, consented real-device sessions, recording tasks and quotes without exposing private messages or ID data. Observe: can each person start/join, distinguish pending from confirmed, recall the agreed meeting point/time/cost, find a way to leave/report, and actually complete or deliberately cancel? Ask privately whether they would use it again for a *specific* activity. Report denominators and failures; do not optimize daily screen time or claim population-level efficacy from a two-person trial.

## Gemini execution board — ordered, testable, and within scope

### G0 — Re-establish a trustworthy baseline (first action, no new features)

**Owner:** Gemini. **Output:** a dated verification record with command, env, DB path type (not secret path contents), source revision/diff state, result, and failure triage.

1. Inspect `git status` before touching files; local source is staged/dirty with no first commit or remote. Use no commands that reset/clean it. Check the six context files, feature 003 and current code contracts.
2. Install the pinned frontend dependencies (`npm ci` in `frontend/`) **before** backend pytest: cross-stack RT-17 invokes TypeScript tooling. Then run backend + disaster-recovery tests with a fresh disposable database and the existing `backend/conftest.py` isolation rules. Run `ops/test_pilot_preflight.py`; include the independent review/security tests. Treat any sandbox `PermissionError` as **no result**, not pass/fail.
3. Run frontend `npm run lint` and `npm run build`. Install pinned `qa/` dependencies if needed. Run the development Playwright suite with **exact** `qa/README.md` test-server setup, including `CARTMATE_MODERATOR_USER_IDS=usr_zuzanna`, a fresh disposable SQLite DB, `SOS_PROVIDER=disabled`, and `CARTMATE_E2E_ISOLATED=1`. Also run the isolated operator-pilot and no-demo suites against their harnesses. Do not point development suites at staging or `cartmate.db`.
4. Reproduce/fix any actual failure and add a focused regression. Publish **new** counts, not inherited counts. If approvals/tooling block a run, record “not run” and the reason.

**Exit:** Full current suites green on the same reviewed source, or an explicit failing-case list and stop. No deployment until this baseline is known.

### G1 — Close the product/safety seams, without feature sprawl

**Owner:** Gemini. **Output:** focused UI/API changes and regressions only where evidence exposes a gap.

- Walk the complete two-person state machine for all activity categories and old shopping rows: create, discover, request, reject/accept, change plan, both accept, chat, PIN, cancel, complete, double-opt-in follow-up. Include retries, out-of-order/duplicate WebSocket frames, disconnection, blocking, suspension, region denial, and lost HTTP response after server commit.
- Independent review must challenge public/private DTOs, age-gate bypasses, moderation/admin access, old session and live socket revocation, group membership, CORS/native destination trust, AI pre-send redaction, and **both Uvicorn and Caddy access logs** for ticket/token leakage. Use OWASP ASVS/MASVS categories and record test payloads without real credentials or user data.
- Verify venue copy and data: specific meeting text is required for new categories, but no endpoint can prove publicness/opening hours/accessibility. Remove any unsupported “safe,” “vetted,” “CCTV,” or “verified venue” labels. If UX research finds the field hard to complete, try a neutral example and confirmation checklist rather than automatic unsafe POI ingestion.
- Confirm block/report/cancel are discoverable from the active trip and chat, including on a 320 CSS px display. Confirm moderator handoff and an unavailable-operator failure path; do not promise 24/7 staffing without an actual rota.

**Exit:** Each identified defect has a minimal patch, regression and human-readable risk note; no new safety claim is introduced.

### G2 — Validate accessibility, language, and low-pressure usability

**Owner:** Gemini for audit/test prep and fixes; founder/participants for observed physical sessions. **Output:** issue log mapped to WCAG 2.2 AA criteria, recording device/OS/browser/assistive tech and retest.

- Inspect complete processes on Android Chrome/TalkBack and, if an iPhone is available, Safari/VoiceOver. Include 200% text/zoom, 320 CSS px equivalent reflow, landscape, reduced-motion, keyboard/focus order, dialog open/close/return, status/live announcements, accessible auth and OTP recovery, 24 CSS px AA pointer-target rule (including its exceptions), contrast, error recovery and hit areas. Test long PL/UK/RU text and the language switch. No “WCAG compliant” claim until an independent whole-process review actually supports it.
- Run `qa/USABILITY_REHEARSAL.md` as **uncoached** tasks with the two adults. Note hesitation and misunderstanding, especially activity selection, pending versus confirmed, cost, venue, cancellation and SOS. Record consent and anonymized observations, not IDs, phone numbers, live location trails, or chat exports.
- Prefer one clear plan/status card and helpful empty states over new feeds, streaks or AI prompts. Add optional reminders only after participants ask for them; specify opt-in, timing, timezone, cancellation and privacy before implementation.

**Exit:** Critical accessibility and comprehension failures fixed and re-observed; remaining issues explicitly prioritized. Emulation alone cannot close this gate.

### G3 — Prepare one EC2 host and a domain-bound Android test build

**Owner:** Founder for AWS/domain/cost/keys; Gemini for reviewed source, deployment procedure and proof, only after founder authorizes access. **Output:** reproducible private deployment and an installed **new** APK with a recorded hash.

1. Before GitHub upload, review staged/untracked content for secrets, databases, backups, activation codes, signing keys and local artifacts. Create a reviewed first commit and **private** remote only with founder-controlled credentials; do not assume this environment is GitHub-authenticated. A repo link is not a live app.
2. Founder follows `ops/EC2_STAGING_RUNBOOK.md` Phase 1: cost check/budget alert, one Frankfurt EC2 host, persistent encrypted EBS, restricted SSH, public 80/443 only, Elastic IP, domain DNS. No NAT gateway/load balancer, extra instance, or paid SMS. Do not share AWS keys, `.env`, private SSH key or activation codes in chat.
3. Deploy the existing Docker Compose + Caddy configuration as one worker with staging operator admission, Jev disabled, SOS SMS disabled and manual 18+ gate. Verify HTTPS, allowed origins, WebSocket upgrade, `/api/health`, **`/api/ready`**, browser auth/authorization and logs. `/api/health` alone is not release readiness.
4. Establish private off-host S3 custody via least-privilege instance role, bucket public access block and encryption. Exercise online backup, transfer both DB + manifest, download and restore to **scratch** DB, run integrity and auth/revocation checks. Never restore a drill into `pilot_live.db`; never use `docker compose down -v` for routine updates.
5. Only after the exact HTTPS hostname works, run `scripts/build_android_apk.ps1 -BackendOrigin "https://YOUR_DOMAIN"`; record SHA-256/signature, install **that exact file** on Android, and check API/WSS origin plus reboot/reconnect. Do not distribute the old APK. iPhone participants use the HTTPS website until a separate iOS build is genuinely tested.

**Exit:** dated cloud/API/TLS/WS evidence, scratch-restore proof, domain-bound APK checksum/installation proof, and an operator rollback/incident procedure. A source clone, APK build, or passing `/api/health` alone is insufficient.

### G4 — Human go/no-go, then a bounded pilot decision

**Owner:** Founder plus a *separately trusted* backup operator; Gemini records evidence and fixes defects. **Output:** completed `qa/PRIVATE_PILOT_REVIEW_RESULTS.md` H-01–H-06 records and signed founder decision.

| Gate | Required observation |
| --- | --- |
| H-01 | Two physical phones on the intended HTTPS network; actual WebSocket updates without reload and recovery after network/server interruption. |
| H-02 | Witnessed adult checks by authorized humans using a supported physical ID method or live official mDowód QR verification; no self-approval, no ID image/number retention. |
| H-03 | Real two-person outing: publish → request → mutual plan → chat → verbal PIN → cancel/complete; test both parties' state and reporting path. Never call 112 in a test. |
| H-04 | Off-EC2 backup custody and scratch restore with data and authorization checks. |
| H-05 | Actual assistive-tech and zoom/usability evidence on physical handsets, with critical defects resolved. |
| H-06 | Named, available operator and backup during a stated pilot window; incident and abuse response route; explicit founder go/no-go. |

**Stop immediately** if a non-participant gets trip/chat/location data; a blocked/revoked user keeps access; a minor/unverified user reaches live matching; SOS copy implies dispatch; the only backup cannot restore; users misread pending as confirmed or cannot leave/report; no responsible human is available; or a test is being run on real user data without consent. Keep invitations closed until the corresponding failure is fixed and retested.

## Decisions only the founder can supply

Gemini should request these *without asking for secrets in chat*: the chosen HTTPS hostname and EC2 instance ID/Elastic IP after cost review; whether the private repo is founder-owned and who grants Git access; the second trusted human operator (not an ordinary participant granted admin just to pass readiness); actual test window and escalation contact; Android model/version(s) and any iPhone; where encrypted off-host backups will be held and who can restore; and permission to invite the first few adults **after** H-01–H-06. A qualified Polish legal/privacy review is needed before wider/public service; do not convert an engineering handoff into a compliance certification.

## Required Gemini handback format

Return one concise, dated matrix: work package, changed files, evidence command/output, defects found and fixed, source revision, remaining risk, and owner. Separate **automated**, **hosted**, and **physical/human** results. Update the top of `GEMINI_HANDOFF.md`, `LAUNCH_READINESS.md`, and `context/progress-tracker.md` only with observed current results, marking old sections historical. Preserve negative evidence and “not run” statuses. End with either **closed-pilot go** (all gates observed and founder authorizes) or **no-go with exact blockers**. Never call this nationwide-launch-ready because a two-person test passed.
