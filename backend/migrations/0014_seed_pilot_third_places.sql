-- Migration 0014: Seed verified pilot Third Places across Katowice, Gliwice, and Chorzów
-- Idempotent seed allowing ordinary users to immediately create micro-pods at verified anchors.

INSERT OR IGNORE INTO third_places (
    slug, name, kind, city, district, address, meeting_point,
    latitude, longitude, is_indoor, verified_at, created_at, updated_at
) VALUES
    ('katowice-biblioteka-slaska', 'Biblioteka Śląska - Hol Główny', 'library', 'Katowice', 'Śródmieście', 'plac Rady Europy 1, Katowice', 'Główne wejście przy recepcji na parterze', 50.2520, 19.0310, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('katowice-trzy-stawy-polana', 'Dolina Trzech Stawów - Przystań', 'park', 'Katowice', 'Muchowiec', 'ul. Trzech Stawów, Katowice', 'Drewniany pomost przy wypożyczalni kajaków', 50.2395, 19.0350, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('katowice-strefa-kultury', 'Strefa Kultury - Plac KTW', 'campus', 'Katowice', 'Bogucice', 'plac Sławika i Antalla 1, Katowice', 'Schody wejściowe przed gmachem NOSPR', 50.2635, 19.0275, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('gliwice-palmiarnia-park', 'Palmiarnia Miejska - Park Chopina', 'park', 'Gliwice', 'Śródmieście', 'ul. Fredry 6, Gliwice', 'Główne wejście do Palmiarni przy fontannie', 50.2985, 18.6790, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('gliwice-rynek-ratusz', 'Rynek w Gliwicach - Podcienia Ratusza', 'community_center', 'Gliwice', 'Stare Miasto', 'Rynek 1, Gliwice', 'Pod arkadami Ratusza naprzeciw fontanny Neptuna', 50.2938, 18.6654, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('gliwice-nowe-gliwice', 'Nowe Gliwice - Dziedziniec Cecha', 'coworking', 'Gliwice', 'Bojków', 'ul. Bojkowska 37, Gliwice', 'Dziedziniec główny przy cechowni (Budynek A)', 50.2780, 18.6835, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('chorzow-park-slaski-rosarium', 'Park Śląski - Rosarium', 'park', 'Chorzów', 'Park Śląski', 'al. Różana, Chorzów', 'Główna pergola przy zegarze słonecznym', 50.2885, 18.9950, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('chorzow-sztygarka', 'Kompleks Sztygarka - Wieża Prezydent', 'community_center', 'Chorzów', 'Klimzowiec', 'ul. Piotra Skargi 34a, Chorzów', 'Plac pod wieżą wyciągową Szybu Prezydent', 50.3015, 18.9620, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('chorzow-mbp-filia', 'Miejska Biblioteka Publiczna w Chorzowie', 'library', 'Chorzów', 'Centrum', 'ul. Sobieskiego 8, Chorzów', 'Strefa czytelni na I piętrze', 50.2970, 18.9540, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z');

INSERT OR IGNORE INTO third_place_templates (third_place_id, template_code)
SELECT id, 'study_sprint' FROM third_places WHERE slug = 'katowice-biblioteka-slaska'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'katowice-biblioteka-slaska'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'katowice-biblioteka-slaska'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'katowice-trzy-stawy-polana'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'katowice-trzy-stawy-polana'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'katowice-strefa-kultury'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'katowice-strefa-kultury'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'gliwice-palmiarnia-park'
UNION ALL SELECT id, 'study_sprint' FROM third_places WHERE slug = 'gliwice-palmiarnia-park'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'gliwice-palmiarnia-park'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'gliwice-rynek-ratusz'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'gliwice-rynek-ratusz'
UNION ALL SELECT id, 'study_sprint' FROM third_places WHERE slug = 'gliwice-nowe-gliwice'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'gliwice-nowe-gliwice'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'chorzow-park-slaski-rosarium'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'chorzow-park-slaski-rosarium'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'chorzow-sztygarka'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'chorzow-sztygarka'
UNION ALL SELECT id, 'study_sprint' FROM third_places WHERE slug = 'chorzow-mbp-filia'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'chorzow-mbp-filia'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'chorzow-mbp-filia';
