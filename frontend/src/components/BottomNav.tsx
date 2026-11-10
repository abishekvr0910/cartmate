import React from 'react';
import { Users, Shield, PlusCircle, MapPin, User as UserIcon } from 'lucide-react';
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
  const isDiscoveryTab = activeTab === 'radar' || activeTab === 'pods' || activeTab === 'voice';

  return (
    <nav className="app-bottom-nav sticky bottom-0 z-30 bg-[#0f172a]/95 backdrop-blur-md border-t border-slate-800/80 px-2 py-2">
      <div className="grid grid-cols-5 items-end gap-1 max-w-lg mx-auto">
        {/* Nearby / Radar Tab (Encompasses Outings, Micro-Pods, Voice) */}
        <button
          onClick={() => onTabChange('radar')}
          aria-current={isDiscoveryTab ? 'page' : undefined}
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-1 py-1 rounded-xl transition-all cursor-pointer ${
            isDiscoveryTab
              ? 'text-emerald-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-5 h-5" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">{t.tabNearby || t.tabRadar}</span>
          {isDiscoveryTab && <span className="w-1 h-1 rounded-full bg-emerald-400" />}
        </button>

        {/* Dedicated Safety Hub Tab */}
        <button
          onClick={() => onTabChange('safety')}
          aria-current={activeTab === 'safety' ? 'page' : undefined}
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-1 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'safety'
              ? 'text-emerald-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Shield className="w-5 h-5" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">{t.tabSafety}</span>
          {activeTab === 'safety' && <span className="w-1 h-1 rounded-full bg-emerald-400" />}
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
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-1 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'active_trip'
              ? 'text-emerald-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <MapPin className="w-5 h-5" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">
            {t.tabTrip}
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
          className={`relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-0.5 px-1 py-1 rounded-xl transition-all cursor-pointer ${
            activeTab === 'profile'
              ? 'text-emerald-400 font-bold scale-105'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <UserIcon className="w-5 h-5" />
          <span className="max-w-full break-words text-center text-[10px] leading-tight">{t.tabProfile}</span>
          {activeTab === 'profile' && <span className="w-1 h-1 rounded-full bg-emerald-400" />}
        </button>
      </div>
      <p role="status" className="sr-only">{hasNewChatActivity ? t.newChatMessage : ''}</p>
    </nav>
  );
};
