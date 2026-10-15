import React, { useState } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import type { Language } from '../locales';
import { translations } from '../locales';

interface PrivacyBannerProps {
  lang: Language;
}

export const PrivacyBanner: React.FC<PrivacyBannerProps> = ({ lang }) => {
  const [dismissed, setDismissed] = useState(false);
  const t = translations[lang];

  if (dismissed) return null;

  return (
    <div className="mx-3 my-2 p-2 rounded-2xl bg-slate-900/90 border border-slate-800/80 shadow-md flex items-center justify-between gap-2.5 backdrop-blur-md">
      <div className="flex items-center gap-2 min-w-0">
        <div className="w-7 h-7 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
          <ShieldCheck className="w-4 h-4" />
        </div>
        <p className="text-[11px] text-slate-300 leading-snug">
          {t.privacyBannerText}
        </p>
      </div>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="flex min-h-11 min-w-11 items-center justify-center text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition shrink-0"
        aria-label={lang === 'pl' ? 'Zamknij informację o prywatności' : 'Dismiss privacy notice'}
        title="Dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
