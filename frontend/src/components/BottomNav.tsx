import React from 'react';
import { Users, PlusCircle, ShieldCheck, MapPin, User as UserIcon } from 'lucide-react';
import type { Trip } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';

export type NavTab = 'radar' | 'new_ping' | 'safety' | 'active_trip' | 'profile';

interface BottomNavProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  activeTrip: Trip | null;
  hasNewChatActivity: boolean;
  lang: Language;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  activeTab,
  onTabChange,
  activeTrip,
  hasNewChatActivity,
  lang,
}) => {
  const t = translations[lang];

  return (
    <nav className="app-bottom-nav sticky bottom-0 z-30 bg-[#0f172a]/95 backdrop-blur-md border-t border-slate-800/80 px-2 py-2">
      <div className="grid grid-cols-5 items-end gap-0.5 max-w-lg mx-auto">
        {/* Nearby People & Trips Tab */}
        <button
          onClick={() => onTabChange('radar')}
          aria-current={activeTab === 'radar' ? 'page' : undefined}
          className={`flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-1 px-0.5 py-1 rounded-xl transition cursor-pointer ${
            activeTab === 'radar'
              ? 'text-emerald-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-[20px] h-[20px]" />
          <span className="max-w-full break-words text-center text-[11px] leading-tight">{t.tabNearby || t.tabRadar}</span>
        </button>

        {/* Safety Hub Tab */}
        <button
          onClick={() => onTabChange('safety')}
          aria-current={activeTab === 'safety' ? 'page' : undefined}
          aria-label={t.tabSafety}
          className={`flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-1 px-0.5 py-1 rounded-xl transition cursor-pointer ${
            activeTab === 'safety'
              ? 'text-emerald-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-[20px] h-[20px]" />
          <span aria-hidden="true" className="max-w-full whitespace-nowrap text-center text-[11px] leading-tight">
            {lang === 'pl' ? 'Bezpiecznie' : t.tabSafety}
          </span>
        </button>

        {/* Create Ping Tab (Center Highlight) */}
        <button
          onClick={() => onTabChange('new_ping')}
          className="flex min-h-[56px] min-w-0 flex-col items-center justify-center -mt-5 cursor-pointer group"
          title={t.tabPost}
        >
          <div className="w-[48px] h-[48px] rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/30 group-hover:scale-105 transition">
            <PlusCircle className="w-[24px] h-[24px] text-slate-950 font-black" />
          </div>
          <span className="max-w-full break-words text-center text-[10px] leading-tight text-emerald-400 font-bold mt-1">{t.tabPost}</span>
        </button>

        {/* Active Trip Tab (with live badge if active) */}
        <button
          onClick={() => onTabChange('active_trip')}
          aria-current={activeTab === 'active_trip' ? 'page' : undefined}
          aria-label={hasNewChatActivity ? `${t.tabTrip}, ${t.newChatMessage}` : t.tabTrip}
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-1 px-0.5 py-1 rounded-xl transition cursor-pointer ${
            activeTab === 'active_trip'
              ? 'text-emerald-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <MapPin className="w-[20px] h-[20px]" />
          <span aria-hidden="true" className="max-w-full whitespace-nowrap text-center text-[11px] leading-tight">
            {lang === 'pl' ? 'Wyjście' : t.tabTrip}
          </span>
          {activeTrip && (
            <span aria-hidden="true" className={`absolute top-1 right-2 w-2.5 h-2.5 rounded-full ring-2 ring-[#0f172a] ${hasNewChatActivity ? 'bg-amber-400' : 'bg-emerald-400'}`} />
          )}
        </button>

        {/* Profile Tab */}
        <button
          onClick={() => onTabChange('profile')}
          aria-current={activeTab === 'profile' ? 'page' : undefined}
          className={`flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-1 px-0.5 py-1 rounded-xl transition cursor-pointer ${
            activeTab === 'profile'
              ? 'text-emerald-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <UserIcon className="w-[20px] h-[20px]" />
          <span className="max-w-full break-words text-center text-[11px] leading-tight">{t.tabProfile}</span>
        </button>
      </div>
      <p role="status" className="sr-only">{hasNewChatActivity ? t.newChatMessage : ''}</p>
    </nav>
  );
};
