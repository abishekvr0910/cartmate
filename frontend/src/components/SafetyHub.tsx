import React, { useState } from 'react';
import {
  ShieldCheck,
  Shield,
  Award,
  CheckCircle2,
  Lock,
  PhoneCall,
  HeartHandshake,
} from 'lucide-react';
import type { User } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';

const SAFETY_COPY: Record<
  Language,
  {
    tierGold: string;
    tierSilver: string;
    tierBronze: string;
    recommended: string;
    demoVerifying: string;
    demoBtn: string;
    idUnavailable: string;
    demoOnlyNotice: string;
    locked: string;
    enabled: string;
    disabled: string;
    safeHavenNotice: string;
    emergencyNotice: string;
    contactSaved: string;
    noContact: string;
    unconfirmedBadge: string;
    call112: string;
    verifyFailed: string;
  }
> = {
  pl: {
    tierGold: 'Złoty',
    tierSilver: 'Srebrny (ID)',
    tierBronze: 'Brązowy',
    recommended: 'Zalecane',
    demoVerifying: 'Tryb demonstracyjny...',
    demoBtn: 'Demo: ustaw status testowy (to nie weryfikuje tożsamości)',
    idUnavailable: 'Weryfikacja tożsamości jest niedostępna — nie połączono prawdziwego dostawcy.',
    demoOnlyNotice: 'Tylko status demonstracyjny — tożsamość nie została zweryfikowana.',
    locked: 'Zablokowane',
    enabled: 'Włączone',
    disabled: 'Wyłączone',
    safeHavenNotice:
      'Gdy Strefa Kobiet jest włączona, Twoje wyjścia będą widoczne wyłącznie dla innych zweryfikowanych kobiet, a na radarze zobaczysz wyjścia dodane przez kobiety.',
    emergencyNotice:
      'Konfiguracja kontaktu alarmowego i potwierdzenie jego zgody nie są jeszcze dostępne. Alert SOS nie zastępuje służb ratunkowych — w bezpośrednim zagrożeniu zadzwoń pod 112.',
    contactSaved: 'Kontakt zapisany — zgoda odbiorcy niepotwierdzona',
    noContact: 'Brak skonfigurowanego kontaktu',
    unconfirmedBadge: 'Niepotwierdzony',
    call112: 'Zadzwoń pod 112 (Numer alarmowy)',
    verifyFailed: 'Weryfikacja nie powiodła się.',
  },
  en: {
    tierGold: 'Gold',
    tierSilver: 'Silver (ID)',
    tierBronze: 'Bronze',
    recommended: 'Recommended',
    demoVerifying: 'Demo mode...',
    demoBtn: 'Demo: set test status (does not verify identity)',
    idUnavailable: 'Identity verification is unavailable; no genuine provider is connected.',
    demoOnlyNotice: 'Demo status only — identity was not verified.',
    locked: 'Locked',
    enabled: 'Enabled',
    disabled: 'Disabled',
    safeHavenNotice:
      'When SafeHaven is turned on, your live pings will only be visible to other ID-verified women, and your radar will filter for women-hosted runs only.',
    emergencyNotice:
      'Emergency-contact setup and recipient consent confirmation are not available yet. SOS does not replace emergency services; call 112 in immediate danger.',
    contactSaved: 'Contact on file — recipient consent unconfirmed',
    noContact: 'No emergency contact configured',
    unconfirmedBadge: 'Unverified',
    call112: 'Call 112 (Emergency services)',
    verifyFailed: 'Verification failed.',
  },
  uk: {
    tierGold: 'Золотий',
    tierSilver: 'Срібний (ID)',
    tierBronze: 'Бронзовий',
    recommended: 'Рекомендовано',
    demoVerifying: 'Демо-режим...',
    demoBtn: 'Демо: встановити тестовий статус (не перевіряє особу)',
    idUnavailable: 'Перевірка особи недоступна — справжній провайдер не підключений.',
    demoOnlyNotice: 'Лише демо-статус — особу не підтверджено.',
    locked: 'Заблоковано',
    enabled: 'Увімкнено',
    disabled: 'Вимкнено',
    safeHavenNotice:
      'Коли безпечний простір увімкнено, ваші виходи бачитимуть лише верифіковані жінки, а на радарі відображатимуться лише події, організовані жінками.',
    emergencyNotice:
      'Налаштування екстреного контакту та згода отримувача ще недоступні. Сигнал SOS не замінює екстрені служби — при загрозі телефонуйте 112.',
    contactSaved: 'Контакт збережено — згоду отримувача не підтверджено',
    noContact: 'Екстрений контакт не налаштовано',
    unconfirmedBadge: 'Непідтверджено',
    call112: 'Зателефонувати 112 (Екстрені служби)',
    verifyFailed: 'Помилка верифікації.',
  },
  ru: {
    tierGold: 'Золотой',
    tierSilver: 'Серебряный (ID)',
    tierBronze: 'Бронзовый',
    recommended: 'Рекомендуется',
    demoVerifying: 'Демо-режим...',
    demoBtn: 'Демо: установить тестовый статус (не проверяет личность)',
    idUnavailable: 'Проверка личности недоступна — реальный провайдер не подключен.',
    demoOnlyNotice: 'Только демо-статус — личность не подтверждена.',
    locked: 'Заблокировано',
    enabled: 'Включено',
    disabled: 'Выключено',
    safeHavenNotice:
      'Когда безопасное пространство включено, ваши выходы видны только подтверждённым женщинам, а радар показывает только встречи, созданные женщинами.',
    emergencyNotice:
      'Настройка экстренного контакта и подтверждение согласия пока недоступны. Сигнал SOS не заменяет экстренные службы — при опасности звоните 112.',
    contactSaved: 'Контакт сохранён — согласие получателя не подтверждено',
    noContact: 'Экстренный контакт не настроен',
    unconfirmedBadge: 'Неподтверждён',
    call112: 'Позвонить 112 (Экстренные службы)',
    verifyFailed: 'Ошибка проверки.',
  },
};

interface SafetyHubProps {
  currentUser: User;
  lang: Language;
  onVerifyId: () => Promise<void>;
  onToggleSafeHaven: () => Promise<void>;
}

export const SafetyHub: React.FC<SafetyHubProps> = ({
  currentUser,
  lang,
  onVerifyId,
  onToggleSafeHaven,
}) => {
  const t = translations[lang];
  const safety = SAFETY_COPY[lang] || SAFETY_COPY.pl;
  const isDemoBuild = import.meta.env.DEV;
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifySuccess, setVerifySuccess] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const handleSimulateVerification = async () => {
    setIsVerifying(true);
    setVerifyError(null);
    try {
      await onVerifyId();
      setVerifySuccess(true);
      setTimeout(() => setVerifySuccess(false), 3000);
    } catch (e: any) {
      setVerifyError(e?.message || safety.verifyFailed);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="p-4 space-y-5 max-w-lg mx-auto pb-24">
      {/* Title */}
      <div>
        <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-emerald-400" />
          <span>{t.safetyHubTitle}</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          {t.safetyHubDesc}
        </p>
      </div>

      {/* 3-Tier Status Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-4 shadow-xl">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
          <span>{t.yourTier}</span>
          <span
            className={`font-black ${
              currentUser.trust_tier === 'Gold'
                ? 'text-amber-400'
                : currentUser.trust_tier === 'Silver'
                ? 'text-emerald-400'
                : 'text-blue-400'
            }`}
          >
            {currentUser.trust_tier === 'Gold'
              ? safety.tierGold
              : currentUser.trust_tier === 'Silver'
              ? safety.tierSilver
              : safety.tierBronze}
          </span>
        </h3>

        {/* Tier steps */}
        <div className="space-y-3">
          {/* Bronze */}
          <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">
                  {currentUser.phone_verified_at ? t.tierBronzeTitle : t.tierBronzeUnconfirmedTitle}
                </span>
                {currentUser.phone_verified_at && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {currentUser.phone_verified_at ? t.tierBronzeDesc : t.tierBronzeUnconfirmedDesc}
              </p>
            </div>
          </div>

          {/* Silver */}
          <div
            className={`flex items-start gap-3 p-3 rounded-xl border transition ${
              currentUser.is_id_verified
                ? 'bg-slate-950/60 border-emerald-500/40'
                : 'bg-emerald-950/20 border-emerald-500/30'
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">{t.tierSilverTitle}</span>
                {currentUser.is_id_verified ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 font-bold px-2 py-0.5 rounded-full border border-emerald-500/40">
                    {safety.recommended}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {t.tierSilverDesc}
              </p>

              {!currentUser.is_id_verified && isDemoBuild && (
                <button
                  onClick={handleSimulateVerification}
                  disabled={isVerifying}
                  className="mt-2.5 w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 rounded-lg transition shadow-md shadow-emerald-500/20 cursor-pointer disabled:opacity-50"
                >
                  {isVerifying ? safety.demoVerifying : safety.demoBtn}
                </button>
              )}

              {!currentUser.is_id_verified && !isDemoBuild && (
                <p className="mt-2 text-[11px] text-amber-300">
                  {safety.idUnavailable}
                </p>
              )}

              {verifySuccess && (
                <p className="text-xs text-emerald-400 font-semibold mt-2 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {safety.demoOnlyNotice}
                </p>
              )}
              {verifyError && (
                <p role="alert" className="text-xs text-rose-300 font-semibold mt-2">
                  {verifyError}
                </p>
              )}
            </div>
          </div>

          {/* Gold */}
          <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
              <Award className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">{t.tierGoldTitle}</span>
                {currentUser.trust_tier === 'Gold' ? (
                  <CheckCircle2 className="w-4 h-4 text-amber-400" />
                ) : (
                  <span className="text-[10px] text-slate-500 font-semibold">
                    {safety.locked}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {t.tierGoldDesc}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Demographic SafeHaven Mode */}
      {currentUser.gender === 'female' && (
        <div className="bg-purple-950/20 border border-purple-500/30 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lock className="w-5 h-5 text-purple-400" />
              <div>
                <h3 className="text-sm font-bold text-white">{t.safeHavenFilter}</h3>
                <p className="text-xs text-purple-300">{t.safeHavenSub}</p>
              </div>
            </div>
            <button
              onClick={onToggleSafeHaven}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition cursor-pointer ${
                currentUser.safe_haven_enabled
                  ? 'bg-purple-600 text-white border-purple-500 shadow-md shadow-purple-500/30'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              {currentUser.safe_haven_enabled ? safety.enabled : safety.disabled}
            </button>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            {safety.safeHavenNotice}
          </p>
        </div>
      )}

      {/* Emergency Contact & In-Trip Protection */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
        <div className="flex items-center gap-2">
          <PhoneCall className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-bold text-white">{t.emergencyContactTitle}</h3>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          {safety.emergencyNotice}
        </p>
        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-200">
            {currentUser.emergency_contact ? safety.contactSaved : safety.noContact}
          </span>
          <span className="text-[10px] text-amber-300 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
            {safety.unconfirmedBadge}
          </span>
        </div>
        <a
          href="tel:112"
          className="w-full py-2.5 px-4 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-rose-200 font-bold text-xs flex items-center justify-center gap-2 transition"
        >
          <PhoneCall className="w-4 h-4 text-rose-400" />
          <span>{safety.call112}</span>
        </a>
      </div>

      {/* Humane Tech Manifesto */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border border-teal-500/20 rounded-2xl p-4 space-y-2.5">
        <div className="flex items-center gap-2">
          <HeartHandshake className="w-5 h-5 text-teal-400" />
          <h3 className="text-sm font-bold text-teal-300">{t.promiseTitle}</h3>
        </div>
        <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
          <li><strong>{t.promise1.split(':')[0]}:</strong> {t.promise1.split(':')[1]}</li>
          <li><strong>{t.promise2.split(':')[0]}:</strong> {t.promise2.split(':')[1]}</li>
          <li><strong>{t.promise3.split(':')[0]}:</strong> {t.promise3.split(':')[1]}</li>
        </ul>
      </div>
    </div>
  );
};

export default SafetyHub;
