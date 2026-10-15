# CartMate frontend UX review — 2026-09-28

This is an engineering/design judgment from local browser screenshots and code review, **not** a usability study or accessibility certification. The screenshots covered 320px, Pixel 7, and 1440px viewports. The local regression suites passed 102/102 backend cases, 26/26 desktop/mobile browser journeys, 4/4 no-demo staging-style browser journeys, plus React build and oxlint. No hosted Render, real SMSAPI, screen-reader lab, or partner cohort was used.

## Candid score

**6/10 overall** for an invited MVP frontend: 6/10 on mobile and 5/10 on desktop. The product has a recognizable visual language, clear public-venue outings, coherent safety disclosures, and a real two-person journey. It is usable enough for a *small supervised pilot after the separate launch gates pass*, but it is not yet at the visual or interaction polish of a leading consumer social app. This score is subjective, not a measured user outcome.

## What changed in this pass

- Real outing cards appear before secondary hotspot voting; intent filters start collapsed on narrow phones. The first outing is visible before the bottom navigation at 320px in the local browser check.
- Removed non-persistent likes/bookmarks, a non-functional share link, implied social-profile verification, and 5-star displays for unrated members. A wave only reports success after the server accepts it.
- Newly registered and seeded users no longer receive unrelated stock-person portraits; initials are the fallback. Reputation is shown only with actual review counts.
- Improved touch targets, focus visibility, reduced-motion handling, concise privacy copy, and 320px navigation labels. Desktop discovery now has two columns rather than a narrow phone feed.

## Benchmark and next design sprint

The relevant bar is not copying another app's look. [Meetup](https://help.meetup.com/hc/en-us/articles/39235072484109-Finding-an-event) gets people to a discoverable nearby activity; [Bumble BFF](https://bumble.com/bff-us/) gives friendship a clear social context; [Timeleft](https://help.timeleft.com/hc/en-150/articles/28530361837212-How-Does-Timeleft-Match-Me-With-a-Group) structures offline group meetings. CartMate's distinction should be a low-pressure, concrete errand with a transparent plan and a safe public meeting place.

1. **One dominant next action.** Make the first-use screen answer “What can I do nearby today?” with one legible outing preview and an honest “Create an outing” path. Keep Feed/Deck/Map as secondary discovery modes until real usage shows each earns its place.
2. **Design system and typography.** Define type sizes, spacing, surfaces, color/contrast, button hierarchy, and icon use across all screens. Increase many 9–11px labels to readable sizes; reduce all-caps and overlapping emoji/badge treatments. Test the hierarchy with Polish copy first, then all four locales.
3. **Trustful people layer.** Add an opt-in, consented profile-photo flow only after abuse/privacy review. Until then, use initials consistently; never assign strangers' portraits or present ratings without reviews. Show the exact reason for each trust badge.
4. **Responsive product surfaces.** Improve desktop navigation and card detail layouts, tablet breakpoints, landscape/small-phone keyboard behavior, zoom to 200%, and empty/low-liquidity states. The current desktop grid is an improvement, not a complete desktop product.
5. **Performance and evidence.** Set a measured mobile performance budget and profile real devices/network conditions. The MapLibre chunk is lazy-loaded but still about 1.06 MB minified; the main chunk is about 507 kB. Run moderated task tests with 8–12 Silesian pilot participants, including screen-reader and reduced-motion users, before claiming top-tier UX.

For accessibility, check the interface against [WCAG 2.2 target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) and [focus appearance](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance), and check iOS safe areas and control sizes against [Apple layout guidance](https://developer.apple.com/design/human-interface-guidelines/layout). Passing the current keyboard/browser smoke tests is not equivalent to meeting these standards everywhere.

The release gates in [LAUNCH_READINESS.md](LAUNCH_READINESS.md) remain in force; visual polish does not substitute for human moderation, privacy review, real carrier OTP, and hosted staging/backup evidence.
