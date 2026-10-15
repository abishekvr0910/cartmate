import React from 'react';
import { Sparkles, MessageSquare, Hand, UserPlus } from 'lucide-react';
import type { LivePing, User } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';
import { UserAvatar } from './UserAvatar';

interface PeopleNearbyCardProps {
  pings: LivePing[];
  currentUser: User;
  lang: Language;
  onSelectPing: (pingId: string) => void;
  onWave: (ping: LivePing) => void;
  onJoin: (ping: LivePing) => void;
  onAsk: (ping: LivePing) => void;
  wavedPingIds?: Record<string, boolean>;
}

export const PeopleNearbyCard: React.FC<PeopleNearbyCardProps> = ({
  pings,
  currentUser,
  lang,
  onSelectPing,
  onWave,
  onJoin,
  onAsk,
  wavedPingIds = {},
}) => {
  const t = translations[lang];

  // Group summary by store/destination for community headline
  const storeCounts: Record<string, number> = {};
  pings.forEach((p) => {
    const store = p.destination_name.split(' ')[0];
    storeCounts[store] = (storeCounts[store] || 0) + 1;
  });

  const storeSummary = Object.entries(storeCounts)
    .slice(0, 3)
    .map(([store, count]) => `${count} w ${store}`)
    .join(' · ');

  return (
    <div className="space-y-3 mt-3">
      {/* Living Neighborhood Header Summary */}
      <div className="p-3.5 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-amber-950/30 border border-slate-800/90 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-bold text-white tracking-wide">
              {pings.length} {t.peopleShoppingNearby}
            </span>
          </div>
          <span className="text-[11px] text-amber-400 font-medium flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-amber-400" />
            {lang === 'pl' ? 'Okolica tętni życiem' : 'Active neighborhood'}
          </span>
        </div>
        {storeSummary && (
          <p className="text-[11px] text-slate-400 mt-1 pl-4.5">
            🛒 {storeSummary} {pings.length > 3 ? `· +${pings.length - 3} więcej` : ''}
          </p>
        )}
      </div>

      {/* People Cards List */}
      <div className="space-y-2.5">
        {pings.map((ping) => {
          const isMe = ping.host.id === currentUser.id;
          const isWaved = !!wavedPingIds[ping.id];
          const firstName = ping.host.name.split(' ')[0];
          const distanceKm = ping.distance_km ?? (ping.distance_miles != null ? ping.distance_miles * 1.60934 : null);
          const distanceStr = distanceKm == null ? null : lang === 'pl' ? `~${distanceKm.toFixed(1)} km stąd` : `~${distanceKm.toFixed(1)} km away`;

          // Human intent description: use ping.notes or fallback friendly text
          const intentDescription =
            ping.notes ||
            (ping.intent_tags && ping.intent_tags.length > 0
              ? ping.intent_tags.join(' • ')
              : lang === 'pl'
              ? 'Wspólne wyjście w publicznym miejscu'
              : 'An outing together in a public place');

          return (
            <div
              key={ping.id}
              className={`p-3.5 rounded-2xl border transition-all ${
                isWaved
                  ? 'bg-amber-950/20 border-amber-500/40 shadow-sm'
                  : 'bg-slate-900/80 hover:bg-slate-900 border-slate-800/80 hover:border-slate-700/80 shadow-md'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                {/* Open the actual outing; an active listing is not online presence. */}
                <button
                  type="button"
                  aria-label={`${lang === 'pl' ? 'Pokaż wyjście' : 'View outing'}: ${ping.destination_name}`}
                  className="flex items-start gap-3 min-w-0 cursor-pointer text-left"
                  onClick={() => onSelectPing(ping.id)}
                >
                  <div className="relative shrink-0">
                    <UserAvatar name={ping.host.name} src={ping.host.avatar} className="w-11 h-11 rounded-full border-2 border-emerald-500/80 text-sm" />
                  </div>

                  {/* Name, Destination & Intent */}
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-sm font-bold text-white truncate hover:text-emerald-300 transition">
                        {firstName}
                      </span>
                      <span className="text-[11px] text-slate-400">·</span>
                      <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2 py-0.5 rounded-lg truncate">
                        {ping.destination_name}
                      </span>
                      {ping.women_only && (
                        <span className="text-[10px] bg-purple-950 text-purple-300 px-1.5 py-0.5 rounded border border-purple-800/40 font-semibold">
                          SafeHaven
                        </span>
                      )}
                    </div>

                    {/* Shared Intent Quote */}
                    <p className="text-xs text-slate-300 mt-1 italic line-clamp-2">
                      “{intentDescription}”
                    </p>

                    {/* Distance / Neighborhood context */}
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-400">
                      {distanceStr && <span>📍 {distanceStr}</span>}
                      {ping.host.reviews_count > 0 && (
                        <>
                          {distanceStr && <span>•</span>}
                          <span>⭐ {ping.host.rating.toFixed(1)} ({ping.host.reviews_count})</span>
                        </>
                      )}
                      {(distanceStr || ping.host.reviews_count > 0) && <span>•</span>}
                      <span className="text-amber-300/90 font-medium">
                        {Math.max(1, Math.round(ping.remaining_seconds / 60))} {lang === 'pl' ? 'min do końca ogłoszenia' : 'min until listing closes'}
                      </span>
                    </div>
                  </div>
                </button>
              </div>

              {/* Lightweight Social Action Row */}
              {!isMe && (
                <div className="mt-3 pt-2.5 border-t border-slate-800/70 flex items-center justify-end gap-2">
                  {/* Wave CTA */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onWave(ping);
                    }}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition active:scale-95 cursor-pointer ${
                      isWaved
                        ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                        : 'bg-slate-800 hover:bg-slate-700/80 text-amber-300 border border-amber-500/30'
                    }`}
                    title={isWaved ? 'Pomachano' : 'Wyślij szybkie pozdrowienie'}
                  >
                    <Hand className="w-3.5 h-3.5" />
                    <span>{isWaved ? '👋 Pomachano!' : t.actionWave}</span>
                  </button>

                  {/* Ask Question CTA */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onAsk(ping);
                    }}
                    className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700/80 text-slate-200 border border-slate-700/70 flex items-center gap-1.5 transition active:scale-95 cursor-pointer"
                  >
                    <MessageSquare className="w-3.5 h-3.5 text-slate-300" />
                    <span>{t.actionAsk}</span>
                  </button>

                  {/* Join Me CTA */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onJoin(ping);
                    }}
                    className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 flex items-center gap-1.5 shadow-md shadow-emerald-500/20 transition active:scale-95 cursor-pointer"
                  >
                    <UserPlus className="w-3.5 h-3.5 text-slate-950" />
                    <span>{t.actionJoin}</span>
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
