import { useEffect, useRef, useState } from 'react';
import { MapPin, Users } from 'lucide-react';
import type { Map as MapLibreMap, Marker as MapLibreMarker } from 'maplibre-gl';
import type { LivePing } from '../types';
import type { Language } from '../locales';
import { POLISH_CITIES } from '../api';

interface OpenNeighborhoodMapProps {
  pings: LivePing[];
  cityName: string;
  selectedPingId: string | null;
  onSelectPing: (pingId: string) => void;
  lang: Language;
}

type MapStatus = 'idle' | 'loading' | 'ready' | 'error';

export function OpenNeighborhoodMap({
  pings,
  cityName,
  selectedPingId,
  onSelectPing,
  lang,
}: OpenNeighborhoodMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const maplibreRef = useRef<typeof import('maplibre-gl') | null>(null);
  const markersRef = useRef<MapLibreMarker[]>([]);
  const [tilesRequested, setTilesRequested] = useState(false);
  const [status, setStatus] = useState<MapStatus>('idle');

  const city = POLISH_CITIES.find((entry) => entry.name === cityName) ?? POLISH_CITIES[0];
  const polish = lang === 'pl';

  useEffect(() => {
    if (!tilesRequested || !mapContainerRef.current) return;
    let cancelled = false;
    let loaded = false;
    let loadTimeout: number | undefined;

    Promise.all([
      import('maplibre-gl'),
      import('maplibre-gl/dist/maplibre-gl.css'),
    ]).then(([maplibre]) => {
      if (cancelled || !mapContainerRef.current) return;
      maplibreRef.current = maplibre;
      const map = new maplibre.Map({
        container: mapContainerRef.current,
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [city.lng, city.lat],
        zoom: 11,
        attributionControl: { compact: false },
      });
      mapRef.current = map;
      map.scrollZoom.disable(); // Scrolling the outing feed must not accidentally zoom the map.
      map.dragRotate.disable();
      map.touchZoomRotate.disableRotation();
      map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right');
      map.once('load', () => {
        loaded = true;
        window.clearTimeout(loadTimeout);
        if (!cancelled) setStatus('ready');
      });
      map.on('error', () => {
        if (!loaded && !cancelled) setStatus('error');
      });
      loadTimeout = window.setTimeout(() => {
        if (!loaded && !cancelled) setStatus('error');
      }, 12000);
    }).catch(() => {
      if (!cancelled) setStatus('error');
    });

    return () => {
      cancelled = true;
      window.clearTimeout(loadTimeout);
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
      maplibreRef.current = null;
    };
  }, [tilesRequested, city.lat, city.lng]);

  useEffect(() => {
    const map = mapRef.current;
    const maplibre = maplibreRef.current;
    if (status !== 'ready' || !map || !maplibre) return;

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];
    const bounds = new maplibre.LngLatBounds();
    for (const ping of pings) {
      if (!Number.isFinite(ping.destination_lat) || !Number.isFinite(ping.destination_lng)) continue;
      const markerButton = document.createElement('button');
      markerButton.type = 'button';
      markerButton.className = 'cartmate-map-pin';
      markerButton.dataset.selected = String(ping.id === selectedPingId);
      markerButton.setAttribute('aria-label', `${ping.host.name}: ${ping.destination_name}`);

      const avatar = document.createElement('img');
      avatar.src = ping.host.avatar;
      avatar.alt = '';
      markerButton.appendChild(avatar);

      const label = document.createElement('span');
      label.textContent = ping.host.name.split(' ')[0];
      markerButton.appendChild(label);
      markerButton.addEventListener('click', () => onSelectPing(ping.id));

      const position: [number, number] = [ping.destination_lng, ping.destination_lat];
      markersRef.current.push(
        new maplibre.Marker({ element: markerButton, anchor: 'bottom' })
          .setLngLat(position)
          .addTo(map)
      );
      bounds.extend(position);
    }
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 48, maxZoom: 12, duration: 0 });
    }
    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
    };
  }, [status, pings, onSelectPing, selectedPingId]);

  return (
    <section className="rounded-3xl overflow-hidden border border-slate-800 bg-slate-900 shadow-xl" aria-label={polish ? 'Mapa miejsc wyjścia' : 'Outing destination map'}>
      <div className="flex flex-wrap items-center justify-between gap-2 p-4">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <MapPin className="h-4 w-4 text-emerald-400" />
          {polish ? `Miejsca wyjść · ${cityName}` : `Outing places · ${cityName}`}
        </div>
        <span className="flex items-center gap-1 text-xs text-emerald-300">
          <Users className="h-3.5 w-3.5" /> {pings.length}
        </span>
      </div>

      {!tilesRequested ? (
        <div className="mx-4 mb-4 flex min-h-[260px] flex-col items-center justify-center gap-3 rounded-2xl border border-emerald-800/40 bg-[radial-gradient(circle_at_center,#164e35_0%,#0f172a_68%)] p-5 text-center">
          <MapPin className="h-9 w-9 text-emerald-400" />
          <p className="max-w-xs text-xs leading-relaxed text-slate-300">
            {polish
              ? 'Pokaż przybliżone okolice publicznych miejsc spotkań na prawdziwej mapie. Nie pokazujemy lokalizacji osób na żywo.'
              : 'See approximate public meeting-place areas on a real map. We do not show people’s live locations.'}
          </p>
          <button
            type="button"
            onClick={() => { setStatus('loading'); setTilesRequested(true); }}
            className="min-h-11 rounded-xl bg-emerald-500 px-5 text-sm font-bold text-slate-950 hover:bg-emerald-400"
          >
            {polish ? 'Otwórz mapę' : 'Open map'}
          </button>
          <p className="max-w-xs text-[10px] text-slate-400">
            {polish
              ? 'Mapa pobiera kafelki z OpenFreeMap; dostawca może widzieć Twój adres IP i oglądany obszar.'
              : 'The map loads tiles from OpenFreeMap, which may see your IP address and viewed area.'}
          </p>
        </div>
      ) : (
        <div className="relative mx-4 mb-3 overflow-hidden rounded-2xl border border-slate-700">
          <div ref={mapContainerRef} className="h-[300px] w-full bg-slate-800" aria-label={polish ? 'Mapa publicznych miejsc' : 'Map of public places'} />
          {status === 'loading' && (
            <div role="status" className="absolute inset-0 grid place-items-center bg-slate-900/80 text-sm text-slate-200">
              {polish ? 'Ładowanie mapy…' : 'Loading map…'}
            </div>
          )}
          {status === 'error' && (
            <div role="alert" className="absolute inset-0 grid place-items-center bg-slate-900/90 p-4 text-center text-xs text-slate-200">
              {polish ? 'Mapa jest teraz niedostępna. Lista wyjść poniżej nadal działa.' : 'Map unavailable. The outing list below still works.'}
            </div>
          )}
        </div>
      )}

      <p className="px-4 pb-4 text-[10px] leading-relaxed text-slate-400">
        {polish
          ? 'Znaczniki pokazują przybliżone okolice celu, nie położenie osób ani potwierdzone wejścia. Dokładne publiczne miejsce zbiórki ustalcie w planie.'
          : 'Pins show approximate destination areas, not people’s locations or verified entrances. Agree on the exact public meeting point in your plan.'}
      </p>
    </section>
  );
}
