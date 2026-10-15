// Curated public-venue areas for the closed GZM pilot. Coordinates are
// approximate orientation points, not verified entrance or live user locations.
export const SILESIA_VENUES = [
  // Address/area: bs.katowice.pl/kontakt/biblioteka-slaska-budynek-glowny/
  { name: 'Biblioteka Śląska (hol główny)', address: 'Plac Rady Europy 1, Katowice', category: 'study', lat: 50.2519, lng: 19.0314 },
  // Public square: portal.katowice.pl/informator-miejsce-rynek
  { name: 'Rynek Katowice', address: 'Rynek, Katowice', category: 'social', lat: 50.2593, lng: 19.0217 },
  { name: 'Kafej / Strefa Kultury', address: 'ul. Uniwersytecka 13, Katowice', category: 'cafe', lat: 50.2575, lng: 19.0260 },
  { name: 'Burger King Katowice Dworzec 24h', address: 'Plac Szewczyka 2, Katowice', category: 'late_night', lat: 50.2580, lng: 19.0175 },
  { name: 'Silesia City Center & Zara', address: 'ul. Chorzowska 107, Katowice', category: 'fashion', lat: 50.2700, lng: 19.0040 },
  { name: 'Galeria Katowicka', address: 'ul. 3 Maja 30, Katowice', category: 'fashion', lat: 50.2580, lng: 19.0175 },
  { name: 'Biedronka Mariacka Katowice', address: 'ul. Mariacka 2, Katowice', category: 'grocery', lat: 50.2570, lng: 19.0270 },
  { name: 'Makro Cash & Carry Katowice', address: 'Al. Roździeńskiego 188, Katowice', category: 'wholesale', lat: 50.2680, lng: 19.0400 },
  { name: 'IKEA Katowice', address: 'Al. Roździeńskiego 95, Katowice', category: 'home', lat: 50.2690, lng: 19.0550 },
  { name: 'Forum Gliwice & Carrefour', address: 'ul. Lipowa 1, Gliwice', category: 'grocery', lat: 50.2945, lng: 18.6714 },
] as const;
