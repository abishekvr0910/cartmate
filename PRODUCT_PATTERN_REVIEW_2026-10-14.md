# CartMate product-pattern review — 2026-10-14

This is a review of **publicly documented product behavior and CartMate source**, not an REA reverse-engineering report. The supplied [REA project](https://github.com/morluto/rea) analyzes a concrete binary, package, JavaScript artifact, or observable runtime. No WhatsApp, Facebook, Messenger, Meetup, Bumble, or Timeleft app package or authenticated runtime was supplied or inspected with REA. Their private code, algorithms, and internal safety effectiveness remain unknown. Do not copy proprietary assets or imply parity with end-to-end encrypted messaging.

## Patterns worth adapting

| Public evidence | What CartMate already has | CartMate-specific opportunity |
| --- | --- | --- |
| [WhatsApp events](https://about.fb.com/news/2024/05/events-in-whatsapp-communities/) make an event findable from the group and expose who is coming; [2026 group updates](https://about.fb.com/news/2026/01/whatsapp-group-chats-member-tags-text-stickers-event-reminders/) add optional event reminders. | Structured plan, mutual acceptance, trip chat, check-in. | Put the agreed plan and participant commitment in one compact trip summary; later test one optional, time-bound reminder rather than a notification stream. |
| [Messenger Communities](https://about.fb.com/news/2024/10/facebook-local-tab-messenger-communities-ai/) connects interest-based local discovery with smaller chats; Facebook Events can accept outside invitations. | Intent-filtered nearby outings and scoped chats. | Keep discovery about a concrete errand, not an endless social feed. Improve handoff from accepted outing to the specific trip conversation. |
| [WhatsApp block/report guidance](https://faq.whatsapp.com/1142481766359885/) provides direct controls, while explicitly noting that blocking alone does not hide messages in a shared group. | Bidirectional block, report, moderation, trip/group authorization. | Keep testing blocked-user isolation in every shared group and event path; expose block/report at the moment of discomfort, without routing a participant through the profile. |
| [Meetup attendee management](https://help.meetup.com/hc/en-us/articles/9389668230541-Managing-my-events-attendees) distinguishes RSVP, waitlist, attendance and cancellation. | Join request, host acceptance, mutual plan approval, PIN presence check, cancellation. | Make each state unmistakable in the UI. Do not label a request as confirmed or a PIN as actual safety certification. A waitlist is unnecessary for the two-person pilot. |
| [Bumble For Friends Plans](https://bumble.com/bff/join-plans) starts with a specific activity near the user; its [product explainer](https://www.safety.bumble.com/the-buzz/bumble-for-friends?amp=1) describes in-app group coordination. | Activity/venue presets and hotspot voting. | Test activity-first copy and a low-effort plan invitation in user interviews before adding new matching machinery. |
| [Timeleft's safety explanation](https://www.timeleft.com/blog/safety-starts-before-the-dinner/) describes public venues and low-friction reporting. | Public rendezvous suggestions, 18+ pilot gate, report/block and direct 112 fallback. | Assess actual venue quality and reporting usability with humans. This is a vendor claim, not independent evidence that its safety model works or transfers to CartMate. |

## Implemented now

Before this slice, `ActiveTripHUD` subscribed to `chat:<room>` only while the Trip tab was mounted. A companion on the Radar tab could miss the live cue entirely, although history reloaded later. `App.tsx` now owns the authorized trip-chat subscription across tabs and sets a quiet, localized activity cue on the Trip tab for a message from the other participant. A screen-reader status announces the cue without exposing message text. Opening the tab or changing trips clears the cue. It is an **in-memory activity hint**, not a persistent unread count, delivery receipt, read receipt, push notification, or message-content preview. `ActiveTripHUD` continues to fetch and deduplicate history. The existing server still authorizes the room subscription and message access.

The targeted two-person Playwright journey passed in desktop Chromium and Pixel 7 emulation after the companion navigated away, received a host message, saw the cue, returned, and saw the message. This does not prove native APK or physical-device behavior.

## Next experiments, not automatic features

1. **Observed usability session:** Ask two admitted adults to create and join one real errand without coaching. Measure whether they can name the agreed time, public meeting spot, cost rule, and exit path. Stop if they misunderstand acceptance or safety claims.
2. **Trip summary design:** Prototype a single readable plan/RSVP/status card in PL/EN/UK/RU; test 320px, 200% zoom and screen-reader order. Keep source of truth server-side.
3. **Optional reminder only if needed:** Ask whether a single opt-in pre-meet reminder helps. Do not add urgency timers, streaks, infinite feeds or engagement pressure. Any notification feature needs explicit permission, timezone handling, cancellation/revocation and privacy review.
4. **Group pilot later:** If two-person journeys work, specify capacity, host accountability, admission, block isolation, member departure and cancellation before adding larger groups. Do not import generic social-network group scale into an unstaffed pilot.

The closed Silesia pilot remains gated by AWS deployment verification and H-01 through H-06 real-world checks. No public launch or claim of WhatsApp/Facebook-level security follows from this review.
