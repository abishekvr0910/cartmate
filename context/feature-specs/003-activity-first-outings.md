# 003 — Activity-first outings for the closed Silesia pilot

Status: Locally implemented; correctly configured full browser-suite retest pending (2026-10-14). This extends ordinary outings, not admission or rollout scope.

## Problem

CartMate promises company for everyday life, but the API categories and creation/discovery UI mostly describe shopping. A study session, walk, gym visit, meal, or simple conversation currently looks like an errand. After mutual follow-up, profile copy again says "shopping buddies". This mismatch obscures the product's purpose.

## Slice and acceptance

1. Preserve existing category values and stored rows. Add distinct `study`, `fitness`, `walk`, `food`, and `social` activity values to backend and frontend contracts. Surface the existing `quick` category as general errands. Users can create and discover each with the same age, admission, region, moderation, block, expiry and mutual-acceptance gates as existing pings.
2. Creation offers a neutral default and concrete public-place guidance, including venue access/cost clarity. Curated pilot examples are orientation points only, not claims about opening hours, public access, or verified entrances.
3. Discovery and all four language labels distinguish the new activities from shopping. Classification suggestions may assist but never override the user's chosen category or authorize an outing.
4. A matched trip's initial description and meeting suggestion must be activity-neutral. For new activity categories, the host must replace the generic meeting suggestion with a specific public point in the plan; the agreed point is then shown to both participants. A no-expected-spend plan can be selected and requires a zero estimated cost. Both participants still must accept final terms before check-in. Shopping/50:50 behavior stays compatible.
5. Mutual follow-up is described as meeting again, regardless of activity. It remains private double opt-in; this slice does not create unsolicited buddy messaging or a hidden invite channel.
6. Add backend contract and authorization regressions, frontend build/lint and targeted browser checks. Keep H-01..H-06 NOT RUN until human/device evidence exists.

## Out of scope

No new external map provider, unverified venue database, public nationwide discovery, algorithmic loneliness scoring, streaks, native APK release, or change to age/SOS policies.

## Observed verification and limits

- 172 backend + disaster-recovery tests passed with a unique disposable SQLite database and shadow-mode regression configuration before the final rendezvous wording correction. New tests cover all five new category values plus the existing `quick` errands category, discovery, privacy, unauthorized host acceptance/plan editing, exact meeting-point requirement, no-expected-spend estimate, deterministic classification and WebSocket log redaction. After replacing legacy unverified "high safety/CCTV" claims with "confirm with participants", the focused existing rendezvous pytest passed 1/1 and a five-branch smoke check passed. A full non-escalated rerun hit a Windows sandbox `PermissionError` while listing pytest's disposable temp directory; it did not produce valid full-suite evidence.
- React build/typecheck and oxlint passed; Vite still warns about two large chunks. Earlier in this slice, the local browser suite passed 42/42 desktop/mobile; after the final advisory-only Jev assertion and errand wording, the targeted activity journey passed 2/2. A later full run passed 40/42: both moderation cases that require `CARTMATE_MODERATOR_USER_IDS=usr_zuzanna` failed because the new test server omitted that documented fixture. The configured fresh-server rerun was blocked before execution by the tool approval usage limit. Do not call the latest full suite green until rerun. The isolated operator-pilot 16/16 and no-demo 4/4 results predate this final UI-only edit.
- Public status of any entered venue or meeting point is **not independently verified** by CartMate. The server requires a specific plan point for the new categories but cannot establish that an arbitrary text address is actually public, open or accessible. The people meeting must confirm it. The classification suggestion is not a safety decision.
- No EC2 deployment, origin-bound APK rebuild, physical handset accessibility/usability session, witnessed age check, or off-host recovery rehearsal was performed. H-01..H-06 remain NOT RUN.
