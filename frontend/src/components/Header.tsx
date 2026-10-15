import React, { useState } from 'react';
import { Shield, ShieldCheck, Award, MapPin, Smartphone, Monitor, ChevronDown, UserCircle2 } from 'lucide-react';
import type { User } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';
import { POLISH_CITIES } from '../api';
import { UserAvatar } from './UserAvatar';

interface HeaderProps {
  currentUser: User;
  lang: Language;
  onSelectLanguage: (lang: Language) => void;
  isMobileFrame: boolean;
  onToggleMobileFrame: () => void;
  onNavigateSafety: () => void;
  selectedCity: string;
  onSelectCity: (cityName: string) => void;
  onOpenAuth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentUser,
  lang,
  onSelectLanguage,
  isMobileFrame,
  onToggleMobileFrame,
  onNavigateSafety,
  selectedCity,
  onSelectCity,
  onOpenAuth,
}) => {
  const t = translations[lang];
  const [isCityDropdownOpen, setIsCityDropdownOpen] = useState(false);
  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState(false);

  const LANGUAGES: { code: Language; label: string; flag: string }[] = [
    { code: 'pl', label: 'Polski', flag: '🇵🇱' },
    { code: 'en', label: 'English', flag: '🇬🇧' },
    { code: 'uk', label: 'Українська', flag: '🇺🇦' },
    { code: 'ru', label: 'Русский', flag: '🇷🇺' },
  ];

  const currentLangObj = LANGUAGES.find((l) => l.code === lang) || LANGUAGES[0];

  const getTierBadge = () => {
    switch (currentUser.trust_tier) {
      case 'Gold':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
            <Award className="w-3.5 h-3.5 text-amber-400" />
            <span>{lang === 'pl' ? 'Złoty' : 'Gold'}</span>
          </span>
        );
      case 'Silver':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>{lang === 'pl' ? 'Srebrny (ID)' : 'Silver (ID)'}</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/40">
            <Shield className="w-3.5 h-3.5 text-blue-400" />
            <span>{lang === 'pl' ? 'Brązowy' : 'Bronze'}</span>
          </span>
        );
    }
  };

  return (
    <header className="app-header sticky top-0 z-30 bg-[#0f172a]/95 backdrop-blur-md border-b border-slate-800/80 px-3.5 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1.5">
        {/* Logo and brand */}
        <div className="flex items-center gap-2 min-w-0 max-w-full">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 shrink-0">
            <span className="text-lg font-black text-slate-950">C</span>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm tracking-tight text-white">{t.appName}</span>
              <span className="hidden min-[370px]:inline text-[9px] font-bold px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
                PL 🇵🇱
              </span>
            </div>

            {/* City Selector Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsCityDropdownOpen(!isCityDropdownOpen)}
                className="flex min-h-11 max-w-full items-center gap-1 text-[11px] text-slate-300 hover:text-white transition-colors cursor-pointer"
              >
                <MapPin className="w-3 h-3 text-emerald-400 shrink-0" />
                <span className="min-w-0 truncate font-semibold underline decoration-dotted decoration-emerald-500/60 underline-offset-2">
                  {selectedCity}
                </span>
                <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
                <span className="text-slate-600 hidden xs:inline">•</span>
                <span className="text-slate-400 hidden xs:inline">{t.radiusDefault}</span>
              </button>

              {isCityDropdownOpen && (
                <div 
                  className="absolute left-0 mt-1.5 w-44 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl py-1.5 z-50 text-xs animate-fade-in"
                  onClick={() => setIsCityDropdownOpen(false)}
                >
                  <div className="px-3 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    {t.citySelectTitle}
                  </div>
                  {POLISH_CITIES.map((c) => (
                    <button
                      key={c.name}
                      type="button"
                      onClick={() => onSelectCity(c.name)}
                      className={`w-full min-h-10 px-3 py-1.5 text-left flex items-center justify-between hover:bg-slate-800 transition-colors ${
                        selectedCity === c.name ? 'text-emerald-400 font-bold bg-slate-800/60' : 'text-slate-300'
                      }`}
                    >
                      <span>{c.label}</span>
                      {selectedCity === c.name && <span className="text-emerald-400 text-xs">✓</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right side controls */}
        <div className="ml-auto flex items-center justify-end gap-1.5 shrink-0">
          {/* User Avatar & Login Switcher */}
          <button
            onClick={onOpenAuth}
            className="flex min-h-11 min-w-11 items-center justify-center gap-1.5 px-2 py-1 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 text-slate-200 transition-all cursor-pointer group"
            title={lang === 'pl' ? 'Logowanie / Zmień konto' : 'Sign in / Switch account'}
          >
            {currentUser.avatar ? (
              <UserAvatar name={currentUser.name} src={currentUser.avatar} className="w-5 h-5 rounded-full border border-emerald-400 text-[8px]" />
            ) : (
              <UserCircle2 className="w-5 h-5 text-emerald-400" />
            )}
            <span className="text-[11px] font-semibold max-w-[65px] truncate hidden sm:inline">
              {currentUser.name.split(' ')[0]}
            </span>
          </button>

          {/* Multi-Language Switcher Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsLangDropdownOpen(!isLangDropdownOpen)}
              className="flex min-h-11 items-center gap-1 text-xs font-bold px-2 py-1 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer"
              title="Wybierz język / Select language / Оберіть мову"
            >
              <span>{currentLangObj.flag}</span>
              <span className="text-[11px] uppercase font-bold">{currentLangObj.code}</span>
              <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
            </button>

            {isLangDropdownOpen && (
              <div 
                className="absolute right-0 mt-1.5 w-40 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl py-1.5 z-50 text-xs animate-fade-in"
                onClick={() => setIsLangDropdownOpen(false)}
              >
                <div className="px-3 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  Język / Language
                </div>
                {LANGUAGES.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => {
                      onSelectLanguage(l.code);
                      setIsLangDropdownOpen(false);
                    }}
                    className={`w-full min-h-10 px-3 py-1.5 text-left flex items-center justify-between hover:bg-slate-800 transition-colors cursor-pointer ${
                      lang === l.code ? 'text-emerald-400 font-bold bg-slate-800/60' : 'text-slate-300'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-sm">{l.flag}</span>
                      <span>{l.label}</span>
                    </span>
                    {lang === l.code && <span className="text-emerald-400 text-xs font-bold">✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Trust tier badge (clickable) */}
          <button
            onClick={onNavigateSafety}
            className="hidden min-[430px]:flex min-h-11 items-center cursor-pointer transition hover:opacity-85"
            title="Weryfikacja i bezpieczeństwo"
          >
            {getTierBadge()}
          </button>

          {/* Toggle device frame preview */}
          <button
            onClick={onToggleMobileFrame}
            className="hidden sm:flex items-center gap-1 text-xs text-slate-400 hover:text-white px-1.5 py-1 rounded-xl bg-slate-800/60 border border-slate-700/60 transition cursor-pointer"
            title={isMobileFrame ? "Pełny ekran" : "Widok telefonu"}
          >
            {isMobileFrame ? (
              <Monitor className="w-3.5 h-3.5 text-teal-400" />
            ) : (
              <Smartphone className="w-3.5 h-3.5 text-teal-400" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
