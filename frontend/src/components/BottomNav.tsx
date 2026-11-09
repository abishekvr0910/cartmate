import React from 'react';
import { Users, PlusCircle, MapPin, User as UserIcon, Sparkles, PhoneCall } from 'lucide-react';
import type { Trip } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';

export type NavTab = 'pods' | 'voice' | 'radar' | 'new_ping' | 'safety' | 'active_trip' | 'profile';

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
      <div className="grid grid-cols-6 items-end gap-0.5 max-w-lg mx-auto">
        {/* Micro-Pods Tab (Primary) */}
        <button
          onClick={() => onTabChange('pods')}
          aria-current={activeTab === 'pods' ? 'page' : undefined}
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-0.5 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'pods'
              ? 'text-indigo-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-[18px] h-[18px]" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">
            {lang === 'pl' ? 'Pody 3-5' : 'Pods'}
          </span>
          {activeTab === 'pods' && <span className="w-1 h-1 rounded-full bg-indigo-400" />}
        </button>

        {/* 10-Minute Voice Calls Tab (Track 2) */}
        <button
          onClick={() => onTabChange('voice')}
          aria-current={activeTab === 'voice' ? 'page' : undefined}
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-0.5 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'voice'
              ? 'text-violet-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <PhoneCall className="w-[18px] h-[18px]" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">
            {lang === 'pl' ? "Głos 10'" : 'Voice'}
          </span>
          {activeTab === 'voice' && <span className="w-1 h-1 rounded-full bg-violet-400" />}
        </button>

        {/* Nearby People & Radar Tab */}
        <button
          onClick={() => onTabChange('radar')}
          aria-current={activeTab === 'radar' ? 'page' : undefined}
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-0.5 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'radar'
              ? 'text-emerald-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-[18px] h-[18px]" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">{t.tabNearby || t.tabRadar}</span>
          {activeTab === 'radar' && <span className="w-1 h-1 rounded-full bg-emerald-400" />}
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
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-0.5 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'active_trip'
              ? 'text-emerald-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <MapPin className="w-[18px] h-[18px]" />
          <span aria-hidden="true" className="max-w-full whitespace-nowrap text-center text-[10px] leading-tight">
            {lang === 'pl' ? 'Wyjście' : t.tabTrip}
          </span>
          {activeTab === 'active_trip' && <span className="w-1 h-1 rounded-full bg-emerald-400" />}
          {activeTrip && (
            <span aria-hidden="true" className={`absolute top-1 right-2 w-2 h-2 rounded-full ring-2 ring-[#0f172a] ${hasNewChatActivity ? 'bg-amber-400' : 'bg-emerald-400'}`} />
          )}
        </button>

        {/* Profile Tab */}
        <button
          onClick={() => onTabChange('profile')}
          aria-current={activeTab === 'profile' ? 'page' : undefined}
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-0.5 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'profile'
              ? 'text-emerald-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <UserIcon className="w-[18px] h-[18px]" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">{t.tabProfile}</span>
          {activeTab === 'profile' && <span className="w-1 h-1 rounded-full bg-emerald-400" />}
        </button>
      </div>
      <p role="status" className="sr-only">{hasNewChatActivity ? t.newChatMessage : ''}</p>
    </nav>
  );
};
