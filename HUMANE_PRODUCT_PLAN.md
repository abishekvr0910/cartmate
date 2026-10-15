# CartMate — humane connection, age safety, and Silesia pilot plan

**Research and planning note — 2026-09-29.** The founder subsequently approved a web-first Poland-wide information strategy and an **18+ invite-only Katowice/GZM live pilot**; this is not a launch approval or a claim that CartMate treats loneliness. The age-assurance method and legal review are still pending, and no age gate exists in code. See the [product narrative and rollout contract](PRODUCT_NARRATIVE_AND_ROLLOUT.md) and the release gates in [LAUNCH_READINESS.md](LAUNCH_READINESS.md).

## What the references actually say

- **The Social Dilemma is a documentary film, not a verified CartMate growth manual.** I reviewed the film's official site and the Center for Humane Technology's (CHT) related public resources, not the full Netflix film or an alleged full transcript. Their central product-design warning is that engagement-led systems can turn attention, social pressure, notifications, and behavioral data into goals in their own right. CHT recommends measuring genuine thriving rather than convenient proxies such as screen time. Sources: [official film](https://thesocialdilemma.com/the-film/), [CHT on social media incentives](https://www.humanetech.com/social-media-society), [CHT humane product principles](https://www.humanetech.com/humane-product-design), [CHT persuasive-technology guide](https://www.humanetech.com/youth/persuasive-technology).
- **The linked Streaks page is a Framer app-launch template, not evidence of a working or popular running app.** The preview presents weekly goals, local clubs, polished device-led storytelling, and a “streaks that pause instead of resetting” message. Its testimonials, adoption figures, stock avatars, and app-store badges must not be treated as real CartMate proof or copied into launch material. Framer lists a *Limited* template license. Use its clarity, rhythm, responsive structure, and tokenized visual system as inspiration; create original CartMate assets and copy. Sources: [Streaks preview](https://streaks.framer.website/), [Framer template listing and license](https://www.framer.com/marketplace/templates/streaks-app-launch/).
- **Age and streaks intersect.** The European Commission's 2025 guidance for platforms accessible to minors recommends disabling engagement-pressure features such as communication streaks by default for children and calls for proportionate, privacy-preserving age assurance. Applicability to CartMate must be assessed by qualified Poland/EU counsel; it is not a claim that a specific EU rule automatically makes every streak unlawful. The EDPB emphasizes purpose limitation and collecting only the age attribute needed for an access decision. Sources: [Commission minors guidance](https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-protection-minors), [EDPB age-assurance statement](https://www.edpb.europa.eu/documents/statement/statement-12025-on-age-assurance_en), [European Commission GDPR children overview](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/legal-grounds-processing-data/are-there-any-specific-safeguards-data-about-children_en).
- **The problem is real, but CartMate's effect is unproven.** WHO describes social connection as the structure, function, *and quality* of relationships. A completed outing alone does not establish reduced loneliness or a safe relationship; pilot research must ask participants about quality and safety without pretending the app is therapy. Sources: [WHO social-connection Q&A](https://www.who.int/news-room/questions-and-answers/item/social-connection), [WHO Commission report](https://www.who.int/publications/i/item/978240112360).
- **Jev is a bounded decision model, not a companion or safety authority.** TypeSafe's official quickstart specifies typed Choice, Score, and Noul outputs at `/v1/systemone`; it does not generate supportive conversations or make a typed output automatically correct. Keep permissions, ages, SOS, identity, money, and human moderation in deterministic code and accountable people. Sources: [official TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart), [TypeSafe's Jev introduction](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

## Product promise and anti-goals

**Promise:** “I have a normal errand or a reason to go outside. CartMate helps me find one nearby, clearly planned, low-pressure outing with another consenting adult, then gets out of the way.”

The unit of value is a **safe, wanted offline experience**, not app opens, messages, swipes, screen time, or an ever-rising public score. A person must be able to browse briefly, decide “not today,” cancel without guilt, and leave without being chased back by notifications.

Do not ship infinite scroll, fake scarcity/social proof, public streak leaderboards, loss-aversion countdowns, “your friend is waiting” nudges, loneliness/vulnerability targeting, paid streak protection, or AI-generated emotional attachment. Do not market an outing as mental-health treatment or a monitored emergency service.

## Age policy: 18+ approved; assurance still required before real invitations

**Approved product policy for the first closed Katowice/GZM pilot: adults 18+ only.** This is a risk decision for offline meetings between strangers, not an assertion that EU law always mandates 18. Until qualified counsel and the founder approve a proportionate assurance method and engineering implements it, the production age gate is **not implemented** and the pilot must not invite users.

1. Specify the underage appeal/removal process, provider/method, privacy notice, retention, and who reviews false denials for the approved 18+ policy. SMS OTP proves phone control, not age or identity. Self-declared age alone should not be described as verified age.
2. Prefer a proof of **over-threshold status and provenance**, not a stored birth date or raw identity document, where a reviewed provider can support it. Restrict processing to age eligibility; do not reuse the signal for advertising, matching, or Jev profiling. Have counsel review method reliability, discrimination, accessibility, GDPR/DSA applicability, and contracts.
3. Enforce the outcome on the server for admission and all discovery/contact paths—not only a signup checkbox. Include API, WebSocket, invite redemption, creating/joining outings, chat, and existing accounts. Fail closed for unknown/unverified age in deployed mode. Test denial, replay, revocation, provider outage, restart persistence, and attempts to bypass the UI.
4. Keep under-18 users out of direct adult/minor pairing. A future youth product, if ever pursued, needs its own safeguarding model, not a minor toggle on adult CartMate.

Current code check: `backend/models.py` and `frontend/src/components/AuthModal.tsx` have no date-of-birth, over-18 provenance, or server-enforced age gate. Existing SMS and ID flags do not fill that gap. **Do not call age safety done.**

## A humane “streak” — proposed, not approved for pilot release

Call the first experiment a **private weekly connection rhythm**, not a daily chat streak. The user chooses whether to enable it. At most one safely completed outing can mark a week; extra outings, messages, and browsing yield no extra progression. Pausing, illness, cancellation, reporting someone, or taking time alone never lowers a public score or triggers a guilt message. There is no leaderboard, expiring flame, or paid freeze. A gentle optional weekly reminder is capped and can be switched off; never say a companion is waiting merely to bring someone back.

The first implementation should be behind a feature flag and preferably **after** age/safety gates and initial user interviews. Prototype two versions—private weekly reflection versus a pausable streak—and ask pilot participants which feels supportive, pressuring, or pointless. Only retain a streak if it improves independently reported outing quality/comfort without increasing unsafe meetings, reports, or compulsive checking. Explicitly test “I stopped using the app because I made a real friend” as a **success**, not churn.

## Jev's bounded role

Current code in `backend/jev_service.py` already has a deterministic baseline, optional TypeSafe call, and shadow audit for intent classification/content screening; `JEV_MODE` defaults to `shadow`. Without configured provider credentials and a representative evaluation set, no real-world accuracy is demonstrated. There is no basis to promote Jev to an autonomous safety or matchmaking authority.

Use Jev only for bounded, explainable assistance: classify a user's outing intent, flag ambiguous text for **human** review, or rank **public** rendezvous suggestions from an approved list. Redact before transmission and do not send private chat, exact coordinates, phone numbers, age documents, or sensitive inferences. Never let it decide whether a user is an adult, verified, eligible for SafeHaven, banned, in danger, or financially owed money. Never produce “compatibility” or loneliness-vulnerability scores.

Promotion out of shadow mode requires a versioned Polish/English/Ukrainian/Russian evaluation set, measured false negatives/positives for harassment and scams, bias checks, appeal paths, human review, latency/failure limits, and a rollback switch. Model confidence is a routing hint, not proof of safety. A provider outage must leave the deterministic baseline and hard policy intact.

## Visual and interaction direction

Translate the Streaks site's *clarity* rather than cloning its dark fitness artwork: one strong promise, clear three-step explanation, original mobile screenshots, visible safety limitations, localized neighborhood photos used with permission, responsive design tokens, and accessible light/dark contrast. Keep CartMate's people-and-places tone warmer than a surveillance dashboard. The in-app home should show a few real, relevant outings and an honest empty state, not an endless social feed. “Create,” “Join,” and “Leave safely” should remain the clearest actions.

Do not publish template testimonials, “500k users,” app-store badges, or fabricated success statistics. A marketing site can add genuine pilot stories **only** with explicit consent, and privacy/terms pages must describe actual deployed behavior. Validate the design at 320px, zoomed text, keyboard, screen reader, reduced motion, and on real low-end phones.

## Order of work and release evidence

| Order | Work | Evidence needed before advancing |
| --- | --- | --- |
| **P0 — no invitations yet** | Founder/counsel select an age-assurance method for the approved 18+ policy; name human safety coverage; complete server-enforced assurance, session/privacy review, retention/deletion, and moderated incident path. | Negative-path tests and independent security/privacy review; unknown or underage accounts cannot discover/contact adults. |
| **P1 — hosted rehearsal** | Private Git + hosted CI, Render Frankfurt persistent storage, SMSAPI single-handset test, backup/offsite restore/rollback, accessibility review. | Real HTTPS/WSS and carrier test records; operator signs the rehearsal. |
| **P2 — Silesia pilot** | One Katowice microarea, public venues and stated hours, voluntary invitations, human moderation, user interviews. | Safe attended outings and participant-reported quality/comfort; no unresolved high-severity safety incidents. |
| **P3 — product experiments** | Original visual-system upgrade, optional weekly-rhythm prototype, Jev shadow evaluation. A Poland-wide information page may be prepared separately with accurate pilot scope and its own privacy/accessibility review; an interest list needs a separate data-policy gate. | A/B or interview evidence of *better offline outcomes* with no safety/pressure regression. |
| **P4 — live-service expansion decision** | Improve or stop based on pilot data; only then consider more Silesian cities, native packaging, or live meetups elsewhere in Poland. | Founder review of cohort, incident, accessibility, provider-cost, and retention evidence. |

Pilot measures: attended PIN-verified outings, voluntary second outing, felt safety and comfort (optional short feedback), cancellations/no-shows, reports/blocks, moderator response, auth/SMS failures, and the number of people who leave the app because they connected offline. Avoid optimizing for daily active users or time-on-screen. Stop invitations for unauthorized access, PII leakage, false safety claims, unstaffed urgent reports, or any unresolved serious harm.

## Founder decisions needed

1. Appoint a Poland/EU privacy/safeguarding reviewer to choose the assurance route, appeal process, and data handling for the **approved 18+** live-service policy.
2. Name the human moderator/safety lead, hours, escalation path, and first voluntary Katowice cohort/venue windows.
3. Provide private Git/Render/SMSAPI rehearsal access already listed in [LAUNCH_READINESS.md](LAUNCH_READINESS.md); the web-first direction is approved.
4. Confirm whether the pausable, private weekly rhythm is worth prototyping **after** safety gates; it is not a launch prerequisite.
