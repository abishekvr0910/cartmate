-- Migration 0016: Withdraw unevidenced verification from the seeded pilot Third Places.
--
-- third_places.verified_at means "checked in person" (migration 0011) and gates pod creation:
-- trg_pods_validate_insert aborts with 'place_unavailable' unless it is set. Migration 0014
-- stamped all nine seeded places with one identical placeholder timestamp and no recorded
-- visit. This migration clears exactly that placeholder, so no pod can be scheduled at a
-- seeded place until a person has actually visited it. A row whose verified_at was later
-- replaced with a real visit time no longer matches the placeholder and is left untouched.
--
-- Restoring verification is a deliberate, per-place operator action after a real visit
-- (visit time in UTC):
--   UPDATE third_places
--      SET verified_at = '<YYYY-MM-DDTHH:MM:SSZ>',
--          updated_at  = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
--    WHERE slug = '<slug>';

UPDATE third_places
   SET verified_at = NULL,
       updated_at  = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
 WHERE verified_at = '2026-11-10T00:00:00Z'
   AND slug IN (
       'katowice-biblioteka-slaska',
       'katowice-trzy-stawy-polana',
       'katowice-strefa-kultury',
       'gliwice-palmiarnia-park',
       'gliwice-rynek-ratusz',
       'gliwice-nowe-gliwice',
       'chorzow-park-slaski-rosarium',
       'chorzow-sztygarka',
       'chorzow-mbp-filia'
   );
