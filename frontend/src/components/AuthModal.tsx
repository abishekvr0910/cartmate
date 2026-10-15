import React, { useState, useEffect } from 'react';
import type { User } from '../types';
import {
  registerUser, switchUser, requestOtp, verifyOtp,
  redeemOperatorActivation, redeemOperatorRecovery, fetchEnvironmentConfig,
} from '../api';
import { translations, type Language } from '../locales';
import { useDialogFocus } from '../hooks/useDialogFocus';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  lang: Language;
  onAuthSuccess: (user: User) => void;
  demoUsers: User[];
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  lang,
  onAuthSuccess,
  demoUsers,
}) => {
  const t = translations[lang];
  const [activeTab, setActiveTab] = useState<'login' | 'register' | 'activate'>('login');
  const [operatorPilotEnabled, setOperatorPilotEnabled] = useState(false);
  
  // Login form state (Provider-backed OTP)
  const [loginIdentifier, setLoginIdentifier] = useState('');
  const [loginCode, setLoginCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpCooldown, setOtpCooldown] = useState(0);
  const [devCodeHint, setDevCodeHint] = useState<string | null>(null);
  
  // Register form state (Silesia launch market default)
  const [regName, setRegName] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regGender, setRegGender] = useState('female');
  const [regCity, setRegCity] = useState('Katowice');
  const [regBio, setRegBio] = useState('');
  const [regCampus, setRegCampus] = useState('');
  const [regOtpCode, setRegOtpCode] = useState('');
  const [regInviteCode, setRegInviteCode] = useState('');
  const [pilotInviteRequired, setPilotInviteRequired] = useState(false);
  const [regOtpSent, setRegOtpSent] = useState(false);
  const [regOtpCooldown, setRegOtpCooldown] = useState(0);
  const [regDevCodeHint, setRegDevCodeHint] = useState<string | null>(null);

  // Operator activation form state (staging pilot only, no SMS)
  const [actToken, setActToken] = useState('');
  const [actName, setActName] = useState('');
  const [actCity, setActCity] = useState('Katowice');
  const [actBio, setActBio] = useState('');
  const [actGender, setActGender] = useState('unspecified');

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useDialogFocus('auth-modal', isOpen, onClose);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    void fetchEnvironmentConfig()
      .then((cfg) => {
        if (!active) return;
        setPilotInviteRequired(cfg.pilot_invite_required === true);
        setOperatorPilotEnabled(cfg.operator_pilot_enabled === true);
      })
      .catch(() => { if (active) setPilotInviteRequired(true); });
    return () => { active = false; };
  }, [isOpen]);

  // 60-second cooldown timer for login OTP
  useEffect(() => {
    if (otpCooldown <= 0) return;
    const interval = setInterval(() => {
      setOtpCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [otpCooldown]);

  // 60-second cooldown timer for register OTP
  useEffect(() => {
    if (regOtpCooldown <= 0) return;
    const interval = setInterval(() => {
      setRegOtpCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [regOtpCooldown]);

  if (!isOpen) return null;

  const handleRequestRegOtp = async () => {
    if (!regPhone.trim()) {
      setErrorMessage(lang === 'pl' ? 'Wprowadź numer telefonu, aby otrzymać kod OTP' : 'Please enter phone number for OTP');
      return;
    }
    if (pilotInviteRequired && !regInviteCode.trim()) {
      setErrorMessage('Wpisz kod zaproszenia do zamkniętego pilotażu.');
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await requestOtp(regPhone.trim(), regInviteCode.trim() || undefined);
      setRegOtpSent(true);
      setRegOtpCooldown(res.resend_cooldown_seconds || 60);
      if (res.dev_code) {
        setRegDevCodeHint(res.dev_code);
        setRegOtpCode(res.dev_code);
      }
      setSuccessMessage(
        lang === 'pl'
          ? `Jednorazowy kod weryfikacyjny został wysłany na: ${res.identifier}`
          : `Verification code sent to: ${res.identifier}`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Błąd wysyłania kodu OTP';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!loginIdentifier.trim()) {
      setErrorMessage(lang === 'pl' ? 'Podaj numer telefonu lub adres e-mail' : 'Please enter phone or email');
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await requestOtp(loginIdentifier.trim());
      setOtpSent(true);
      setOtpCooldown(res.resend_cooldown_seconds || 60);
      if (res.dev_code) {
        setDevCodeHint(res.dev_code);
        setLoginCode(res.dev_code);
      }
      setSuccessMessage(
        lang === 'pl'
          ? `Jednorazowy kod weryfikacyjny został wysłany na: ${res.identifier}`
          : `One-time code sent to: ${res.identifier}`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Błąd wysyłania kodu OTP';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginCode.trim()) {
      setErrorMessage(lang === 'pl' ? 'Wprowadź kod weryfikacyjny' : 'Please enter verification code');
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await verifyOtp(loginIdentifier.trim(), loginCode.trim());
      setSuccessMessage(res.message);
      setTimeout(() => {
        onAuthSuccess(res.user);
        onClose();
      }, 600);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Nieprawidłowy kod weryfikacyjny';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim() || !regEmail.trim() || !regPhone.trim()) {
      setErrorMessage(lang === 'pl' ? 'Wypełnij wymagane pola (imię, email, telefon)' : 'Please fill all required fields');
      return;
    }
    if (!regOtpCode.trim()) {
      setErrorMessage(lang === 'pl' ? 'Pobierz i wprowadź kod weryfikacyjny OTP dla telefonu' : 'Please verify phone OTP code before registering');
      return;
    }
    if (pilotInviteRequired && !regInviteCode.trim()) {
      setErrorMessage('Wpisz kod zaproszenia do zamkniętego pilotażu.');
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await registerUser({
        name: regName.trim(),
        email: regEmail.trim(),
        phone: regPhone.trim(),
        gender: regGender,
        city: regCity,
        bio: regBio.trim() || undefined,
        campus_badge: regCampus.trim() || undefined,
        otp_code: regOtpCode.trim(),
        invite_code: regInviteCode.trim() || undefined,
      });
      setSuccessMessage(res.message);
      setTimeout(() => {
        onAuthSuccess(res.user);
        onClose();
      }, 800);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Błąd rejestracji';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoLogin = async (user: User) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const switched = await switchUser(user.id);
      setSuccessMessage(
        lang === 'pl'
          ? `Zalogowano jako ${switched.name}!`
          : `Signed in as ${switched.name}!`
      );
      setTimeout(() => {
        onAuthSuccess(switched);
        onClose();
      }, 500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Błąd przełączania';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = actToken.trim().toUpperCase();
    if (!token) {
      setErrorMessage('Wpisz kod aktywacyjny otrzymany od operatora (CMACT-... lub CMREC-...).');
      return;
    }

    if (token.startsWith('CMREC-')) {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const res = await redeemOperatorRecovery(token);
        setSuccessMessage(res.message || 'Konto zostało pomyślnie odzyskane.');
        setTimeout(() => {
          onAuthSuccess(res.user);
          onClose();
        }, 800);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Błąd odzyskiwania konta';
        setErrorMessage(msg);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    if (!actName.trim() || actName.trim().length < 2) {
      setErrorMessage('Podaj imię i nazwisko (min. 2 znaki).');
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await redeemOperatorActivation({
        activation_token: token,
        name: actName.trim(),
        city: actCity,
        bio: actBio.trim() || undefined,
        gender: actGender,
      });
      setSuccessMessage(
        res.message ||
        'Konto aktywowane. Operator potwierdzi teraz na żywo, że masz 18+.'
      );
      setTimeout(() => {
        onAuthSuccess(res.user);
        onClose();
      }, 900);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Błąd aktywacji konta';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      id="auth-modal"
      className="app-dialog fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/70 backdrop-blur-md animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      tabIndex={-1}
    >
      <div 
        className="w-full max-w-md max-h-[calc(100dvh-1.5rem)] flex flex-col bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-y-auto text-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="relative px-4 sm:px-6 pt-6 pb-4 border-b border-slate-800/80 bg-gradient-to-b from-slate-800/50 to-transparent">
          <button
            onClick={onClose}
            aria-label="Zamknij okno autoryzacji"
            className="absolute top-4 right-4 w-10 h-10 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            ✕
          </button>
          
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl" aria-hidden="true">🛍️</span>
            <span className="text-xs font-semibold tracking-wider uppercase text-emerald-400 bg-emerald-950/70 px-2.5 py-0.5 rounded-full border border-emerald-800/50">
              CartMate Polska 🇵🇱
            </span>
          </div>
          
          <h2 id="auth-modal-title" className="text-xl font-bold text-white tracking-tight">
            {activeTab === 'login'
              ? t.authTitleLogin
              : activeTab === 'register'
              ? t.authTitleRegister
              : 'Kod aktywacyjny pilotażu'}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {activeTab === 'activate'
              ? 'Konto bez SMS — dostęp wyłącznie przez operator pilotażu, weryfikacja 18+ jest wymagana oddzielnie.'
              : lang === 'pl'
              ? 'Wyjdź z kimś na spacer, naukę, trening, jedzenie lub zwykłą sprawę. Dostęp wymaga osobnego sprawdzenia 18+.'
              : 'Walk, study, train, eat or run an errand together. Access requires a separate 18+ check.'}
          </p>

          {/* Tab Switcher */}
          <div className={`grid gap-1.5 mt-4 p-1 bg-slate-950/60 rounded-xl border border-slate-800 ${operatorPilotEnabled ? 'grid-cols-3' : 'grid-cols-2'}`}>
            <button
              type="button"
              onClick={() => { setActiveTab('login'); setErrorMessage(null); setSuccessMessage(null); }}
              className={`min-h-10 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'login'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.authTabLogin}
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab('register'); setErrorMessage(null); setSuccessMessage(null); }}
              className={`min-h-10 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'register'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.authTabRegister}
            </button>
            {operatorPilotEnabled && (
              <button
                type="button"
                onClick={() => { setActiveTab('activate'); setErrorMessage(null); setSuccessMessage(null); }}
                className={`min-h-10 py-2 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === 'activate'
                    ? 'bg-sky-600 text-white shadow-md shadow-sky-900/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                aria-label="Aktywuj kod operatora pilotażu"
              >
                🔑 Aktywuj
              </button>
            )}
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="px-4 sm:px-6 py-5 space-y-4 shrink-0">
          {errorMessage && (
            <div role="alert" className="p-3 text-xs bg-rose-950/60 border border-rose-800 text-rose-300 rounded-xl flex items-start gap-2">
              <span className="text-rose-400">⚠️</span>
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div role="status" className="p-3 text-xs bg-emerald-950/60 border border-emerald-800 text-emerald-300 rounded-xl flex items-start gap-2">
              <span className="text-emerald-400">✅</span>
              <span>{successMessage}</span>
            </div>
          )}

          {activeTab === 'login' ? (
            <div className="space-y-4">
              {!otpSent ? (
                /* Step 1: Identifier Entry */
                <form onSubmit={handleRequestOtp} className="space-y-4">
                  <div>
                    <label htmlFor="auth-login-phone" className="block text-xs font-semibold text-slate-300 mb-1.5">
                      {t.authIdentifierLabel}
                    </label>
                    <div className="relative">
                      <input
                        id="auth-login-phone"
                        type="text"
                        value={loginIdentifier}
                        onChange={(e) => setLoginIdentifier(e.target.value)}
                        placeholder={t.authIdentifierPlaceholder}
                        className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                      />
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Wprowadź numer telefonu — wyślemy jednorazowy kod SMS.
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading || !loginIdentifier.trim()}
                    className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm shadow-lg shadow-emerald-900/30 transition-all active:scale-[0.99] flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <span>Wysyłanie kodu...</span>
                    ) : (
                      <>
                        <span>📲</span>
                        <span>Wyślij kod SMS</span>
                      </>
                    )}
                  </button>
                </form>
              ) : (
                /* Step 2: Code Verification */
                <form onSubmit={handleVerifyOtp} className="space-y-4 animate-fade-in">
                  <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
                    <div>
                      <span className="text-slate-400">Wysłano do: </span>
                      <span className="text-emerald-400 font-mono font-semibold">{loginIdentifier}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => { setOtpSent(false); setErrorMessage(null); }}
                      className="text-emerald-400 hover:underline text-[11px]"
                    >
                      Zmień
                    </button>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label htmlFor="auth-login-code" className="text-xs font-semibold text-slate-300">
                        Kod weryfikacyjny (6 cyfr)
                      </label>
                      {devCodeHint && (
                        <span className="text-[11px] text-emerald-400 font-mono">
                          Kod testowy: {devCodeHint}
                        </span>
                      )}
                    </div>
                    <input
                      id="auth-login-code"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      autoFocus
                      value={loginCode}
                      onChange={(e) => setLoginCode(e.target.value)}
                      maxLength={6}
                      placeholder="• • • • • •"
                      className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2.5 text-lg text-center font-mono tracking-[0.5em] text-emerald-400 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>
                      {otpCooldown > 0 ? (
                        <span>Ponowne wysłanie za: <strong className="text-emerald-400 font-mono">{otpCooldown}s</strong></span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleRequestOtp()}
                          disabled={isLoading}
                          className="text-emerald-400 hover:underline"
                        >
                          Wyślij kod ponownie
                        </button>
                      )}
                    </span>
                    <span className="text-[11px]">Ważność: 5 min</span>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading || !loginCode.trim()}
                    className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm shadow-lg shadow-emerald-900/30 transition-all active:scale-[0.99] flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <span>Weryfikacja...</span>
                    ) : (
                      <>
                        <span>🔐</span>
                        <span>Zweryfikuj i zaloguj</span>
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* Development-only demo logins; never show the section in deployed bundles. */}
              {demoUsers.length > 0 && <div className="pt-3 border-t border-slate-800/80">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                  {t.authDemoQuickLogin}
                </p>
                <div className="grid grid-cols-1 min-[380px]:grid-cols-2 gap-2">
                  {demoUsers.map((u) => (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => handleQuickDemoLogin(u)}
                      disabled={isLoading}
                      className="p-2.5 bg-slate-950/60 hover:bg-slate-800/90 border border-slate-800 rounded-xl text-left flex items-center gap-2.5 transition-all group"
                    >
                      <img
                        src={u.avatar}
                        alt={u.name}
                        className="w-9 h-9 rounded-full object-cover border border-slate-700 group-hover:border-emerald-400 transition-colors"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-semibold text-slate-200 group-hover:text-emerald-400 truncate">
                          {u.name}
                        </div>
                        <div className="text-[10px] text-slate-400 flex items-center gap-1">
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            u.trust_tier === 'Gold' ? 'bg-amber-400' : u.trust_tier === 'Silver' ? 'bg-cyan-400' : 'bg-emerald-400'
                          }`} />
                          <span>{u.trust_tier} • {u.city || 'Katowice'}</span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>}
            </div>
          ) : activeTab === 'register' ? (
            /* Register Form */
            <form onSubmit={handleRegister} className="space-y-3.5">
              <div>
                <label htmlFor="auth-register-name" className="block text-xs font-semibold text-slate-300 mb-1">
                  {t.authFullName} *
                </label>
                <input
                  id="auth-register-name"
                  type="text"
                  required
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="np. Piotr Wiśniewski"
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 min-[380px]:grid-cols-2 gap-2.5">
                <div>
                  <label htmlFor="auth-register-phone" className="block text-xs font-semibold text-slate-300 mb-1">
                    Telefon *
                  </label>
                  <input
                    id="auth-register-phone"
                    type="tel"
                    required
                    value={regPhone}
                    onChange={(e) => setRegPhone(e.target.value)}
                    placeholder="+48 600 000 000"
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label htmlFor="auth-register-email" className="block text-xs font-semibold text-slate-300 mb-1">
                    E-mail *
                  </label>
                  <input
                    id="auth-register-email"
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="kontakt@example.pl"
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              {pilotInviteRequired && (
                <div>
                  <label htmlFor="auth-register-invite" className="block text-xs font-semibold text-slate-300 mb-1">
                    Kod zaproszenia do pilotażu *
                  </label>
                  <input
                    id="auth-register-invite"
                    type="text"
                    required
                    autoComplete="off"
                    value={regInviteCode}
                    onChange={(e) => setRegInviteCode(e.target.value.toUpperCase())}
                    placeholder="CM-…"
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-emerald-500"
                  />
                  <p className="mt-1 text-[11px] text-slate-400">
                    Kod jest jednorazowy. Otrzymasz go bezpośrednio od organizatora pilotażu, nie od pracodawcy ani akademika.
                  </p>
                </div>
              )}

              {/* Phone OTP Verification */}
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <label htmlFor="auth-register-otp" className="font-semibold text-slate-300">Weryfikacja numeru telefonu (OTP) *</label>
                  {regDevCodeHint && (
                    <span className="text-[11px] text-emerald-400 font-mono">
                      Kod testowy: {regDevCodeHint}
                    </span>
                  )}
                </div>
                <div className="flex flex-col min-[380px]:flex-row gap-2">
                  <input
                    id="auth-register-otp"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={regOtpCode}
                    onChange={(e) => setRegOtpCode(e.target.value)}
                    placeholder="Kod SMS (6 cyfr)"
                    maxLength={6}
                    className="w-full min-[380px]:w-1/2 min-h-10 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm font-mono text-center tracking-widest text-emerald-400 focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="button"
                    onClick={handleRequestRegOtp}
                    disabled={isLoading || !regPhone.trim() || regOtpCooldown > 0}
                    className="min-h-10 flex-1 px-3 py-1.5 bg-emerald-700/60 hover:bg-emerald-600 disabled:opacity-50 text-xs font-semibold text-white rounded-lg transition-colors"
                  >
                    {regOtpCooldown > 0
                      ? `Odczekaj (${regOtpCooldown}s)`
                      : regOtpSent
                      ? 'Wyślij ponownie'
                      : 'Pobierz kod SMS'}
                  </button>
                </div>
                <p className="text-[10px] text-slate-400">
                  Kod SMS potwierdza dostęp do numeru telefonu. Nie potwierdza tożsamości właściciela.
                </p>
              </div>

              <div className="grid grid-cols-1 min-[380px]:grid-cols-2 gap-2.5">
                <div>
                  <label htmlFor="auth-register-city" className="block text-xs font-semibold text-slate-300 mb-1">
                    {t.authCity}
                  </label>
                  <select
                    id="auth-register-city"
                    value={regCity}
                    onChange={(e) => setRegCity(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="Katowice">Katowice 🏙️ (Śląsk — Start)</option>
                    <option value="Gliwice">Gliwice 🏛️ (Śląsk)</option>
                    <option value="Sosnowiec">Sosnowiec 🛍️ (Śląsk)</option>
                    <option value="Zabrze">Zabrze 🏭 (Śląsk)</option>
                    <option value="Chorzów">Chorzów 🌳 (Śląsk)</option>
                    <option value="Tychy">Tychy 🌲 (Śląsk)</option>
                    <option value="Bytom">Bytom 🏺 (Śląsk)</option>
                    <option value="Dąbrowa Górnicza">Dąbrowa Górnicza 🌊 (Śląsk)</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="auth-register-gender" className="block text-xs font-semibold text-slate-300 mb-1">
                    {t.authGender}
                  </label>
                  <select
                    id="auth-register-gender"
                    value={regGender}
                    onChange={(e) => setRegGender(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="female">Kobieta (Female)</option>
                    <option value="male">Mężczyzna (Male)</option>
                    <option value="other">Inna (Other)</option>
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="auth-register-campus" className="block text-xs font-semibold text-slate-300 mb-1">
                  Uczelnia (deklarowana, niezweryfikowana; opcjonalnie)
                </label>
                <input
                  id="auth-register-campus"
                  type="text"
                  value={regCampus}
                  onChange={(e) => setRegCampus(e.target.value)}
                  placeholder="np. Uniwersytet Śląski, Politechnika Śląska"
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label htmlFor="auth-register-bio" className="block text-xs font-semibold text-slate-300 mb-1">
                  {t.authBio}
                </label>
                <textarea
                  id="auth-register-bio"
                  rows={2}
                  value={regBio}
                  onChange={(e) => setRegBio(e.target.value)}
                  placeholder="np. Lubię spacery, wspólną naukę i spokojne rozmowy..."
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-xl text-[11px] text-emerald-300/90 leading-relaxed">
                🛡️ <strong>Bezpieczeństwo:</strong> Nowe konto otrzymuje poziom Brązowy po potwierdzeniu numeru SMS. Weryfikacja dokumentu i biometryczna nie są obecnie dostępne.
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm shadow-lg shadow-emerald-900/30 transition-all active:scale-[0.99] flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <span>{t.authRegistering}</span>
                ) : (
                  <>
                    <span>✨</span>
                    <span>{t.authRegisterBtn}</span>
                  </>
                )}
              </button>
            </form>
          ) : activeTab === 'activate' ? (
            /* Operator Activation Form — staging pilot only, no SMS, no fake phone_verified_at */
            <form onSubmit={handleActivate} className="space-y-4 animate-fade-in">
              {/* Honest provenance notice */}
              <div className="p-3 bg-sky-950/50 border border-sky-800/50 rounded-xl text-[11px] text-sky-200/90 leading-relaxed space-y-1">
                <p><strong>🔑 Pilot operatora — bez SMS</strong></p>
                <p>To konto nie wymaga numeru telefonu. Operator wręcza Ci jednorazowy kod osobiście po sprawdzeniu Twojej tożsamości. Kod jest ważny 24 h i wygasa po jednym użyciu.</p>
                <p className="text-sky-300/70">Wejście do wyjść wymaga <strong>oddzielnego</strong> potwierdzenia 18+ przez operatora (na żywo, po aktywacji).</p>
              </div>

              {/* Activation token */}
              <div>
                <label htmlFor="auth-act-token" className="block text-xs font-semibold text-slate-300 mb-1">
                  Kod aktywacyjny (CMACT-...) *
                </label>
                <input
                  id="auth-act-token"
                  type="text"
                  required
                  autoFocus
                  autoComplete="off"
                  spellCheck={false}
                  value={actToken}
                  onChange={(e) => setActToken(e.target.value.toUpperCase())}
                  placeholder="CMACT-..."
                  maxLength={36}
                  className="w-full bg-slate-950/80 border border-sky-800 rounded-xl px-3.5 py-2.5 text-sm font-mono text-sky-200 placeholder-slate-500 focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-colors"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Otrzymasz go bezpośrednio od organizatora pilotażu. Nigdy nie wpisuj go na stronie, której nie znasz.
                </p>
              </div>

              {/* Display name */}
              <div>
                <label htmlFor="auth-act-name" className="block text-xs font-semibold text-slate-300 mb-1">
                  Imię i nazwisko *
                </label>
                <input
                  id="auth-act-name"
                  type="text"
                  required
                  value={actName}
                  onChange={(e) => setActName(e.target.value)}
                  placeholder="np. Anna Kowalska"
                  minLength={2}
                  maxLength={50}
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-sky-400"
                />
              </div>

              {/* City and gender */}
              <div className="grid grid-cols-1 min-[380px]:grid-cols-2 gap-2.5">
                <div>
                  <label htmlFor="auth-act-city" className="block text-xs font-semibold text-slate-300 mb-1">
                    Miasto
                  </label>
                  <select
                    id="auth-act-city"
                    value={actCity}
                    onChange={(e) => setActCity(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="Katowice">Katowice 🏙️</option>
                    <option value="Gliwice">Gliwice 🏛️</option>
                    <option value="Sosnowiec">Sosnowiec 🛍️</option>
                    <option value="Zabrze">Zabrze 🏭</option>
                    <option value="Chorzów">Chorzów 🌳</option>
                    <option value="Tychy">Tychy 🌲</option>
                    <option value="Bytom">Bytom 🏺</option>
                    <option value="Dąbrowa Górnicza">Dąbrowa Górnicza 🌊</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="auth-act-gender" className="block text-xs font-semibold text-slate-300 mb-1">
                    Płeć
                  </label>
                  <select
                    id="auth-act-gender"
                    value={actGender}
                    onChange={(e) => setActGender(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-400"
                  >
                    <option value="unspecified">Nie podano</option>
                    <option value="female">Kobieta</option>
                    <option value="male">Mężczyzna</option>
                    <option value="other">Inna</option>
                  </select>
                </div>
              </div>

              {/* Optional bio */}
              <div>
                <label htmlFor="auth-act-bio" className="block text-xs font-semibold text-slate-300 mb-1">
                  Opis (opcjonalnie)
                </label>
                <textarea
                  id="auth-act-bio"
                  rows={2}
                  value={actBio}
                  onChange={(e) => setActBio(e.target.value)}
                  maxLength={300}
                  placeholder="np. Lubię spacery, kawę i wspólną naukę..."
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-sky-400"
                />
              </div>

              {/* What happens next — honest pending state */}
              <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-xl text-[11px] text-amber-200/80 leading-relaxed">
                ⏳ <strong>Po aktywacji:</strong> Twoje konto zostanie utworzone, ale wyjścia i odkrywanie osób pozostają zablokowane do czasu, gdy operator potwierdzi Ci na żywo, że masz ukończone 18 lat. Weryfikacja 18+ nie jest samodzielna — wymaga obecności operatora.
              </div>

              <button
                type="submit"
                disabled={isLoading || !actToken.trim() || !actName.trim()}
                className="w-full py-3 bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm shadow-lg shadow-sky-900/30 transition-all active:scale-[0.99] flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <span>Aktywowanie...</span>
                ) : (
                  <>
                    <span>🔑</span>
                    <span>Aktywuj konto pilotażu</span>
                  </>
                )}
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </div>
  );
};
