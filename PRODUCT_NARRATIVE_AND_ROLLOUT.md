# CartMate — product narrative and Poland rollout contract

**Decision recorded 2026-09-29; implementation note 2026-09-30. Status: approved product direction, not a launch or legal-compliance approval.** The founder approved a web-first Poland strategy and an **18+ live service**, with real outings starting in the invite-only Katowice/GZM pilot. A fail-closed age-admission guard now exists, but the founder has not chosen an assurance method; no real provider or proof integration exists, so deployed live participation remains closed. [LAUNCH_READINESS.md](LAUNCH_READINESS.md) remains the release gate. The national interest-list data handling, human operating model, and live deployment still need implementation and review.

## The promise

**Polish working line:** “Zwykłe wyjście. Dobre towarzystwo.”

**Plain-language promise:** “Masz coś do zrobienia albo chcesz wyjść z domu? CartMate pomaga znaleźć drugą dorosłą osobę do krótkiego, jasno zaplanowanego wyjścia w publicznym miejscu. Oboje decydujecie, czy chcecie iść; możecie też zrezygnować.”

CartMate is a way to make ordinary offline plans together. It is **not** a dating app, courier marketplace, mental-health treatment, emergency dispatch service, identity guarantee, or promise that every meeting will be safe. The value is a wanted, comfortable real-world outing—not time in the feed, daily app use, swipes, message volume, or a public streak. See the evidence and humane-design constraints in [HUMANE_PRODUCT_PLAN.md](HUMANE_PRODUCT_PLAN.md).

The first useful journey is: find a genuine nearby plan → see time, duration, public meeting place, and cost rule → request to join → both people accept the same plan → coordinate with bounded chat → meet or cancel without guilt → optionally report, block, or independently opt into meeting again. No fabricated activity, verification badges, or success claims.

## Two different geographic promises

| Surface | Initial scope | What a visitor may do | Release condition |
| --- | --- | --- | --- |
| Public web information | Poland-wide, in Polish first | Learn the real product, its 18+ policy, current pilot area, safety limitations, and how expansion decisions work. | Accurate copy, accessibility, privacy/legal review, and no unsupported store badges or social proof. |
| Optional city-interest list | Poland-wide **only after separately approved** | Voluntarily express interest in a future city; this is **not** an account, invitation, outing, or launch-date promise. | Reviewed lawful basis and notice, minimal contact/city data, separate marketing preference if needed, unsubscribe/deletion, retention, abuse controls, and accessibility. No interest-list endpoint exists today. An information-only page can precede it. |
| Live member discovery, posting, joining, chat, and meetups | Invite-only Katowice/GZM pilot; current server boundary is approximately 35 km from Katowice, not all of Śląskie | Eligible adults may use real outings in the active area after all admission checks. | Independent, server-enforced 18+ assurance **plus** SMS phone control and a single-use invitation; hosted, safety, privacy, and operational gates pass. |
| Additional meetup cities | None approved yet | No live posting or cross-city matching until each city is enabled. | Evidence from the pilot, local density, named moderation coverage, city-specific venue/safety review, a new release decision, and server-side geographic enforcement. |

“Available on the web across Poland” means the public information can be seen nationwide; it does **not** mean public signup or user-generated meetup posts are open nationwide. Outside the active area, the UI must say that outings are unavailable rather than showing a fake empty nationwide feed or silently accepting an out-of-area plan. Publishing a marketing post about CartMate is different from allowing a user to publish an outing.

## Eligibility and honest trust language

- **Product rule:** live CartMate is for adults 18+ only. This is a risk decision for offline meetings, **not** a claim that Polish or EU law imposes a universal 18-year minimum on social apps. Poland's online-services GDPR consent threshold is a separate question; [UODO explains the under-16 parental-consent context](https://uodo.gov.pl/pl/493/2261).
- **Current code:** invitation and SMS OTP exist, but age proof does **not**. SMS proves control of a number, not adulthood or identity. No real user should be invited until the missing age boundary is designed, implemented, tested, and independently reviewed.
- **Required design:** a qualified Poland/EU privacy and safeguarding reviewer selects a proportionate, accessible assurance route. Prefer a verifiable “over 18” result and provenance over CartMate storing a birth date, PESEL, or identity image. Do not call self-declaration “verified.” The [EDPB age-assurance statement](https://www.edpb.europa.eu/documents/statement/statement-12025-on-age-assurance_en) requires privacy and proportionality.
- **Fail-closed admission:** unknown, failed, expired, revoked, or unverifiable age status cannot access people, outings, requests, chat, or their WebSocket equivalents in staging/production. Cover existing accounts and active sessions, not just the signup form. Design an accessible false-denial appeal and underage-account removal path. Test provider outage, retry/replay, restart, and API bypasses.
- **Separate trust signals:** an over-18 result, SMS control, and identity verification are different claims. Women-only/SafeHaven features remain disabled until genuine identity verification is integrated and reviewed. Jev does not decide any of these states.

## Safety, content, and privacy contract

First meetings use public, reachable places and explicit plans. Users can leave, cancel, block, and report without a punitive streak or forced review. A named human safety lead must own report coverage, escalation, and the ability to pause invitations; an AI model or a queue without staffed coverage is not a safety service. SMS SOS stays disabled in the pilot; urgent danger directs the person to call **112** themselves. Do not imply live monitoring or delivered emergency alerts.

User-created outings and chat make content governance a real operating duty. A Poland/EU adviser must classify the service and check the applicable GDPR, Polish law, and [EU Digital Services Act](https://eur-lex.europa.eu/eli/reg/2022/2065/oj) duties, including notices, moderation decisions, user redress, and terms. DSA obligations vary by service category and enterprise size; do not assume a blanket small-company exemption. [UODO reported](https://uodo.gov.pl/pl/138/4587) the signing of Poland's first DSA implementation law on 28 September 2026; counsel must check the promulgated text and commencement date before launch. Because CartMate processes location and arranges offline contact, assess whether a GDPR data-protection impact assessment is required before live use; [EDPB guidance](https://www.edpb.europa.eu/topics/accountability-and-compliance-tools/data-protection-impact-assessment_en) describes the high-risk test. This is a legal-review checklist, **not** a claim that compliance has already been achieved.

Keep exact home/work addresses and private contact details out of discovery. Publish only honest, coarse location and public rendezvous information at the appropriate stage. Define and implement retention, export, erasure, incident evidence preservation, session protection, and provider data processing before recruitment. Do not share participant activity with dormitories, employers, or other distribution partners; joining must be voluntary.

## What Jev and a weekly rhythm may do later

Jev may assist with bounded intent classification, content-review triage, or suggestions drawn from approved public meeting places. It remains in shadow mode until representative multilingual evaluation, false-positive/negative measurement, human review, and rollback are demonstrated. It never determines age, eligibility, identity, bans, SOS, payments, or emotional compatibility.

An optional **private, pausable weekly reflection** may be tested after the first safety gates. It is not a launch requirement. No public leaderboards, expiring flames, loss-aversion notifications, guilt for cancellation, or claims that more app use means less loneliness. A real friendship that makes the app unnecessary is a success.

## Execution order and ownership

1. **Admission and legal design — founder + qualified reviewer + backend owner.** Approve an age-assurance method, false-denial process, privacy notice, data retention, and DSA/GDPR classification. Implement durable over-18 provenance and fail-closed guards for registration/admission, existing sessions, discovery, outing actions, chat, and WebSockets. Add negative-path tests and independent authorization review. Until then, no live invitations.
2. **Safety operations and privacy — founder/safety lead + engineering.** Name coverage hours and escalation owner; implement alerts to humans, incident pause, retention/export/erasure and browser-session hardening. Rehearse reports, suspension, and recovery. A green automated suite alone cannot sign this off.
3. **Hosted Silesia rehearsal — operator + independent QA.** Private Git and hosted CI; Docker/Render Frankfurt with persistent storage, HTTPS/WSS, private SMSAPI credentials and a consenting test handset; real OTP/outage test; encrypted offsite backup, restore, and rollback; screen-reader/zoom and security review. Preserve the existing local `backend/cartmate.db` only as a potentially test-contaminated local file, never as a deployment source.
4. **Poland-wide information surface — frontend + privacy reviewer.** Publish a clear, original, accessible web page saying **18+, Silesia pilot**, with accurate safety limitations and no fake metrics. An optional national city-interest form is a separate feature and may ship only after its data lifecycle and legal basis are approved; do not quietly turn it into an open member signup.
5. **Small Katowice cohort — founder + human safety lead.** Invite a voluntary, geographically concentrated adult cohort in public-venue/time windows. Review genuine attendance, comfort, cancellations, reports, moderator response, SMS failures, and user interviews. Pause for serious unresolved safety issues. Only then consider the next area.

**Current evidence is local, not a release:** the last verified snapshot is 108/108 backend tests, 36/36 local browser cases across development and no-demo harnesses, a clean React build/lint, and a 2/2 sample backup drill. Those numbers predate the new age and national-surface work. No live age provider, national interest form, hosted Render/SMSAPI rehearsal, independent legal/security/accessibility sign-off, or real-user outcome has been demonstrated. See [LAUNCH_READINESS.md](LAUNCH_READINESS.md) for the current board and [GEMINI_HANDOFF.md](GEMINI_HANDOFF.md) for contributor boundaries.
