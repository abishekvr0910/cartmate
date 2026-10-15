import React, { useState, useEffect } from 'react';
import { UserAvatar } from './UserAvatar';
import {
  ShieldCheck,
  Star,
  Sparkles,
  UserCheck,
  Building,
  LogOut,
  UserPlus,
  Mail,
  Phone,
  MapPin,
  Flame,
  Link2,
  CheckCircle2,
  Camera,
  Briefcase,
  Music,
  Globe,
  Plus,
  Trash2,
  Smartphone,
  UserX,
  HeartHandshake,
} from 'lucide-react';
import type { CommunityStats, User, ShoppingBuddySchema, SessionInfoSchema, BlockedUserSchema } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';
import { ModeratorConsole } from './ModeratorConsole';
import {
  connectSocialAccount,
  disconnectSocialAccount,
  fetchMyBuddies,
  fetchActiveSessions,
  revokeOtherSessions,
  fetchMyBlocks,
  fetchModerationAccess,
  unblockUser,
} from '../api';

interface ProfileViewProps {
  currentUser: User;
  allUsers: User[];
  stats: CommunityStats | null;
  lang: Language;
  onSwitchUser: (userId: string) => Promise<void>;
  onNavigateSafety: () => void;
  onOpenAuth: () => void;
  onLogout: () => void;
  onUserUpdated?: (user: User) => void;
}

export const ProfileView: React.FC<ProfileViewProps> = ({
  currentUser,
  allUsers,
  stats,
  lang,
  onSwitchUser,
  onNavigateSafety,
  onOpenAuth,
  onLogout,
  onUserUpdated,
}) => {
  const t = translations[lang];

  // Buddies, Sessions & Blocks State
  const [buddies, setBuddies] = useState<ShoppingBuddySchema[]>([]);
  const [sessions, setSessions] = useState<SessionInfoSchema[]>([]);
  const [blocks, setBlocks] = useState<BlockedUserSchema[]>([]);
  const [isRevokingSessions, setIsRevokingSessions] = useState(false);
  const [canModerate, setCanModerate] = useState(false);
  const [showModerationConsole, setShowModerationConsole] = useState(false);

  useEffect(() => {
    let isCancelled = false;
    async function loadData() {
      try {
        const [buddiesList, sessionsList, blocksList, moderatorAccess] = await Promise.all([
          fetchMyBuddies().catch(() => []),
          fetchActiveSessions().catch(() => []),
          fetchMyBlocks().catch(() => []),
          fetchModerationAccess().catch(() => false),
        ]);
        if (!isCancelled) {
          setBuddies(buddiesList);
          setSessions(sessionsList);
          setBlocks(blocksList);
          setCanModerate(moderatorAccess);
        }
      } catch (err) {
        console.error('Failed to load profile safety data:', err);
      }
    }
    loadData();
    return () => { isCancelled = true; };
  }, [currentUser.id]);

  const handleRevokeOtherSessions = async () => {
    try {
      setIsRevokingSessions(true);
      const res = await revokeOtherSessions();
      alert(
        lang === 'pl'
          ? `Unieważniono ${res.revoked_count} pozostałych sesji. Wszystkie pozostałe urządzenia zostały wylogowane.`
          : `Revoked ${res.revoked_count} sessions across other devices.`
      );
      const updatedSessions = await fetchActiveSessions().catch(() => []);
      setSessions(updatedSessions);
    } catch (err: any) {
      alert(err.message || 'Błąd unieważniania sesji');
    } finally {
      setIsRevokingSessions(false);
    }
  };

  const handleUnblockUser = async (userId: string) => {
    try {
      await unblockUser(userId);
      setBlocks((prev) => prev.filter((b) => b.user.id !== userId));
      alert(lang === 'pl' ? 'Użytkownik został odblokowany.' : 'User unblocked.');
    } catch (err: any) {
      alert(err.message || 'Błąd odblokowania użytkownika');
    }
  };

  // Social Connect Modal State
  const [socialModalProvider, setSocialModalProvider] = useState<'instagram' | 'linkedin' | 'tiktok' | 'facebook' | null>(null);
  const [socialInputHandle, setSocialInputHandle] = useState('');
  const [isProcessingSocial, setIsProcessingSocial] = useState(false);

  const handleOpenConnect = (provider: 'instagram' | 'linkedin' | 'tiktok' | 'facebook') => {
    setSocialModalProvider(provider);
    const existing =
      provider === 'instagram' ? currentUser.instagram_handle :
      provider === 'linkedin' ? currentUser.linkedin_handle :
      provider === 'tiktok' ? currentUser.tiktok_handle :
      currentUser.facebook_handle;
    setSocialInputHandle(existing || '');
  };

  const handleConfirmConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!socialModalProvider || !socialInputHandle.trim()) return;

    try {
      setIsProcessingSocial(true);
      const updated = await connectSocialAccount(socialModalProvider, socialInputHandle.trim());
      if (onUserUpdated) onUserUpdated(updated);
      setSocialModalProvider(null);
      setSocialInputHandle('');
    } catch (err: any) {
      alert(err.message || 'Błąd łączenia profilu społecznościowego');
    } finally {
      setIsProcessingSocial(false);
    }
  };

  const handleDisconnect = async (provider: 'instagram' | 'linkedin' | 'tiktok' | 'facebook') => {
    try {
      setIsProcessingSocial(true);
      const updated = await disconnectSocialAccount(provider);
      if (onUserUpdated) onUserUpdated(updated);
    } catch (err: any) {
      alert(err.message || 'Błąd odłączania profilu');
    } finally {
      setIsProcessingSocial(false);
    }
  };

  if (showModerationConsole && canModerate) {
    return <ModeratorConsole lang={lang} onBack={() => setShowModerationConsole(false)} />;
  }

  return (
    <div className="p-4 space-y-5 max-w-lg mx-auto pb-24">
      {canModerate && (
        <button
          type="button"
          onClick={() => setShowModerationConsole(true)}
          className="flex w-full items-center gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-left text-amber-100 hover:bg-amber-500/15"
        >
          <ShieldCheck className="h-5 w-5 shrink-0" aria-hidden="true" />
          <span>
            <span className="block font-bold">{lang === 'pl' ? 'Kolejka bezpieczeństwa' : 'Safety review queue'}</span>
            <span className="mt-0.5 block text-xs text-amber-100/70">{lang === 'pl' ? 'Dostęp tylko dla upoważnionych moderatorów' : 'Available only to authorized moderators'}</span>
          </span>
        </button>
      )}

      {/* Current User Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3.5">
            <div className="relative">
              <UserAvatar name={currentUser.name} src={currentUser.avatar} className="w-16 h-16 rounded-full border-2 border-emerald-500 shadow-md text-lg" />
              <span className={`absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-slate-900 ${
                currentUser.trust_tier === 'Gold' ? 'bg-amber-400' : currentUser.trust_tier === 'Silver' ? 'bg-emerald-400' : 'bg-blue-400'
              }`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-black text-white">{currentUser.name}</h2>
                {currentUser.trust_tier === 'Gold' ? (
                  <span className="bg-amber-500/20 text-amber-300 text-xs font-bold px-2 py-0.5 rounded-full border border-amber-500/40">
                    {lang === 'pl' ? 'Złoty' : 'Gold'}
                  </span>
                ) : currentUser.trust_tier === 'Silver' ? (
                  <span className="bg-emerald-500/20 text-emerald-300 text-xs font-bold px-2 py-0.5 rounded-full border border-emerald-500/40">
                    {lang === 'pl' ? 'Srebrny' : 'Silver'}
                  </span>
                ) : (
                  <span className="bg-blue-500/20 text-blue-300 text-xs font-bold px-2 py-0.5 rounded-full border border-blue-500/40">
                    {lang === 'pl' ? 'Brązowy' : 'Bronze'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">{currentUser.bio}</p>
              
              <div className="flex flex-wrap items-center gap-2 mt-1.5 text-[11px] text-slate-300">
                <span className="flex items-center gap-1 text-emerald-400 font-medium">
                  <MapPin className="w-3 h-3" />
                  {currentUser.city || 'Katowice'}
                </span>
                {currentUser.campus_badge && (
                  <span className="flex items-center gap-1 text-teal-400 font-semibold">
                    <Building className="w-3 h-3" />
                    {currentUser.campus_badge} ({lang === 'pl' ? 'deklaracja' : 'self-reported'})
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Contact & Verification Meta */}
        <div className="grid grid-cols-2 gap-2 text-xs bg-slate-950/70 p-2.5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center gap-1.5 text-slate-400 truncate">
            <Mail className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="truncate">
              {currentUser.email.endsWith('@cartmate.invalid') || /^\d{6}@cartmate\.pl$/.test(currentUser.email)
                ? (lang === 'pl' ? 'E-mail niepodany' : lang === 'uk' ? 'Е-пошту не вказано' : lang === 'ru' ? 'Эл. почта не указана' : 'No email provided')
                : currentUser.email}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-400 truncate">
            <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="truncate">{currentUser.phone}</span>
          </div>
        </div>

        {/* Impact Numbers */}
        <div className="grid grid-cols-3 gap-2 pt-1">
          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 text-center">
            <span className="text-base font-black text-emerald-400">{currentUser.trips_completed}</span>
            <p className="text-[10px] text-slate-400 font-medium">{t.sharedTrips}</p>
          </div>
          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 text-center">
            <span className="text-base font-black text-amber-400 flex items-center justify-center gap-0.5">
              {currentUser.reviews_count > 0 ? (
                <><Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />{currentUser.rating.toFixed(1)}</>
              ) : '—'}
            </span>
            <p className="text-[10px] text-slate-400 font-medium">{t.ratingLabel} ({currentUser.reviews_count})</p>
          </div>
          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 text-center">
            <span className="text-base font-black text-teal-400">
              {currentUser.reviews_count}
            </span>
            <p className="text-[10px] text-slate-400 font-medium">
              {lang === 'pl' ? 'Opinie uczestników' : lang === 'uk' ? 'Відгуки учасників' : lang === 'ru' ? 'Отзывы участников' : 'Participant reviews'}
            </p>
          </div>
        </div>

        {/* Manner Temperature Barometer (Karrot / Daangn Market 36.5°C Model) */}
        {currentUser.reviews_count > 0 && (
        <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-3.5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-base">🌡️</span>
              <div>
                <h4 className="text-xs font-bold text-slate-200">{t.mannerTempTitle}</h4>
                <p className="text-[10px] text-slate-400">{t.mannerTempSub}</p>
              </div>
            </div>
            <div className="text-right">
              <span className={`text-base font-black flex items-center justify-end gap-1 ${
                (currentUser.manner_temperature || 36.5) >= 38.0 ? 'text-amber-400' : 'text-emerald-400'
              }`}>
                {(currentUser.manner_temperature || 36.5).toFixed(1)}°C
                {(currentUser.manner_temperature || 36.5) >= 38.0 && (
                  <Flame className="w-4 h-4 text-orange-400 fill-orange-400 inline" />
                )}
              </span>
              <span className="text-[10px] text-slate-400 block font-medium">baza: 36.5°C</span>
            </div>
          </div>

          {/* Visual Thermal Bar */}
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                (currentUser.manner_temperature || 36.5) >= 40.0
                  ? 'bg-gradient-to-r from-emerald-500 via-amber-400 to-orange-500'
                  : (currentUser.manner_temperature || 36.5) >= 37.0
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                  : 'bg-emerald-500'
              }`}
              style={{
                width: `${Math.min(100, Math.max(10, ((currentUser.manner_temperature || 36.5) - 30) * 5))}%`,
              }}
            />
          </div>

          <p className="text-[10px] text-slate-500">
            {lang === 'pl' ? 'Wskaźnik opiera się na opiniach uczestników; nie jest niezależną weryfikacją.' : 'This score is based on participant reviews; it is not independent verification.'}
          </p>
        </div>
        )}

        {/* Actions row */}
        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800">
          <button
            onClick={onNavigateSafety}
            className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs py-2 rounded-xl transition cursor-pointer flex items-center justify-center gap-1.5"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>{t.viewCredentials}</span>
          </button>
          
          <button
            onClick={onOpenAuth}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs py-2 rounded-xl transition cursor-pointer flex items-center justify-center gap-1.5 shadow-md shadow-emerald-950"
          >
            <UserPlus className="w-4 h-4" />
            <span>{t.switchAccountBtn}</span>
          </button>
        </div>

        <button
          onClick={onLogout}
          className="w-full text-slate-400 hover:text-rose-400 text-xs py-1.5 transition flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>{t.logoutBtn}</span>
        </button>
      </div>

      {/* Social linking is a local demo only; there is no deployed OAuth flow. */}
      {import.meta.env.DEV && (
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Link2 className="w-5 h-5 text-indigo-400" />
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                {t.socialProofTitle}
              </h3>
              <p className="text-[11px] text-slate-400">{t.socialProofSub}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
          {/* Instagram */}
          <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600 flex items-center justify-center text-white shadow-md">
                <Camera className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-bold text-white block">Instagram</span>
                {currentUser.instagram_handle ? (
                  <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                    {currentUser.instagram_handle}
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  </span>
                ) : (
                  <span className="text-[10px] text-slate-500 font-medium">Niepołączone</span>
                )}
              </div>
            </div>

            {currentUser.instagram_handle ? (
              <button
                type="button"
                onClick={() => handleDisconnect('instagram')}
                disabled={isProcessingSocial}
                className="text-[11px] text-slate-400 hover:text-rose-400 p-1.5 rounded-lg hover:bg-slate-900 transition cursor-pointer"
                title={t.socialDisconnectBtn}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleOpenConnect('instagram')}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-1"
              >
                <Plus className="w-3 h-3 text-emerald-400" />
                <span>{t.socialConnectBtn}</span>
              </button>
            )}
          </div>

          {/* LinkedIn */}
          <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md">
                <Briefcase className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-bold text-white block">LinkedIn</span>
                {currentUser.linkedin_handle ? (
                  <span className="text-[11px] text-blue-400 font-medium flex items-center gap-1">
                    in/{currentUser.linkedin_handle}
                    <CheckCircle2 className="w-3 h-3 text-blue-400" />
                  </span>
                ) : (
                  <span className="text-[10px] text-slate-500 font-medium">Niepołączone</span>
                )}
              </div>
            </div>

            {currentUser.linkedin_handle ? (
              <button
                type="button"
                onClick={() => handleDisconnect('linkedin')}
                disabled={isProcessingSocial}
                className="text-[11px] text-slate-400 hover:text-rose-400 p-1.5 rounded-lg hover:bg-slate-900 transition cursor-pointer"
                title={t.socialDisconnectBtn}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleOpenConnect('linkedin')}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-1"
              >
                <Plus className="w-3 h-3 text-emerald-400" />
                <span>{t.socialConnectBtn}</span>
              </button>
            )}
          </div>

          {/* TikTok */}
          <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-teal-400 shadow-md">
                <Music className="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <span className="text-xs font-bold text-white block">TikTok</span>
                {currentUser.tiktok_handle ? (
                  <span className="text-[11px] text-cyan-400 font-medium flex items-center gap-1">
                    {currentUser.tiktok_handle}
                    <CheckCircle2 className="w-3 h-3 text-cyan-400" />
                  </span>
                ) : (
                  <span className="text-[10px] text-slate-500 font-medium">Niepołączone</span>
                )}
              </div>
            </div>

            {currentUser.tiktok_handle ? (
              <button
                type="button"
                onClick={() => handleDisconnect('tiktok')}
                disabled={isProcessingSocial}
                className="text-[11px] text-slate-400 hover:text-rose-400 p-1.5 rounded-lg hover:bg-slate-900 transition cursor-pointer"
                title={t.socialDisconnectBtn}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleOpenConnect('tiktok')}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-1"
              >
                <Plus className="w-3 h-3 text-emerald-400" />
                <span>{t.socialConnectBtn}</span>
              </button>
            )}
          </div>

          {/* Facebook */}
          <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md">
                <Globe className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-bold text-white block">Facebook</span>
                {currentUser.facebook_handle ? (
                  <span className="text-[11px] text-indigo-400 font-medium flex items-center gap-1">
                    {currentUser.facebook_handle}
                    <CheckCircle2 className="w-3 h-3 text-indigo-400" />
                  </span>
                ) : (
                  <span className="text-[10px] text-slate-500 font-medium">Niepołączone</span>
                )}
              </div>
            </div>

            {currentUser.facebook_handle ? (
              <button
                type="button"
                onClick={() => handleDisconnect('facebook')}
                disabled={isProcessingSocial}
                className="text-[11px] text-slate-400 hover:text-rose-400 p-1.5 rounded-lg hover:bg-slate-900 transition cursor-pointer"
                title={t.socialDisconnectBtn}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleOpenConnect('facebook')}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-1"
              >
                <Plus className="w-3 h-3 text-emerald-400" />
                <span>{t.socialConnectBtn}</span>
              </button>
            )}
          </div>
        </div>
      </div>
      )}

      {/* Mutual follow-up only; no unsolicited contact permission. */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <HeartHandshake className="w-5 h-5 text-indigo-400" />
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                {t.mutualConnectionsTitle}
              </h3>
              <p className="text-[11px] text-slate-400">
                {t.mutualConnectionsDesc}
              </p>
            </div>
          </div>
          <span className="text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
            {buddies.length}
          </span>
        </div>

        {buddies.length === 0 ? (
          <div className="bg-slate-950/70 p-3.5 rounded-2xl border border-slate-800 text-center">
            <p className="text-xs text-slate-400 leading-relaxed">
              {t.mutualConnectionsEmpty}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {buddies.map((buddy) => (
              <div
                key={buddy.buddy_user.id}
                className="bg-slate-950 p-3 rounded-2xl border border-slate-800 flex items-center justify-between"
              >
                <div className="flex items-center gap-2.5">
                  <UserAvatar name={buddy.buddy_user.name} src={buddy.buddy_user.avatar} className="w-9 h-9 rounded-full border border-indigo-500/40 text-xs" />
                  <div>
                    <span className="text-xs font-bold text-white block">{buddy.buddy_user.name}</span>
                    <span className="text-[10px] text-indigo-300">
                      {buddy.shared_trips_count} {t.sharedOutings}
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-medium">
                  {t.mutualContact}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Account Security & Active Sessions Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Smartphone className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                {lang === 'pl' ? 'Bezpieczeństwo Sesji i Urządzenia' : 'Active Sessions & Security'}
              </h3>
              <p className="text-[11px] text-slate-400">
                {lang === 'pl'
                  ? 'Zarządzanie aktywnymi tokenami logowania i unieważnianie sesji.'
                  : 'Manage active login tokens and revoke remote sessions.'}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          {sessions.map((sess, idx) => (
            <div
              key={idx}
              className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <div>
                  <span className="font-mono text-slate-300 block">{sess.token_masked}</span>
                  <span className="text-[10px] text-slate-500">
                    {sess.is_revoked
                      ? (lang === 'pl' ? 'Unieważniona' : 'Revoked')
                      : (lang === 'pl' ? 'Sesja aktywna' : 'Active session')}
                  </span>
                </div>
              </div>
              {!sess.is_revoked && (
                <span className="text-[10px] text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-full border border-emerald-500/30 font-semibold">
                  {lang === 'pl' ? 'Aktywna' : 'Active'}
                </span>
              )}
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={handleRevokeOtherSessions}
          disabled={isRevokingSessions || sessions.length <= 1}
          className="w-full bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 font-semibold text-xs py-2 rounded-xl transition cursor-pointer flex items-center justify-center gap-1.5"
        >
          <LogOut className="w-3.5 h-3.5 text-rose-400" />
          <span>
            {isRevokingSessions
              ? (lang === 'pl' ? 'Unieważnianie...' : 'Revoking...')
              : (lang === 'pl' ? 'Wyloguj ze wszystkich pozostałych urządzeń' : 'Revoke all other sessions')}
          </span>
        </button>
      </div>

      {/* Blocked Users Management Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <UserX className="w-5 h-5 text-rose-400" />
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                {lang === 'pl' ? 'Zablokowani użytkownicy' : 'Blocked Users'}
              </h3>
              <p className="text-[11px] text-slate-400">
                {lang === 'pl'
                  ? 'Użytkownicy, którzy nie widzą Twojego profilu ani wyjść na radarze.'
                  : 'Users bidirectionally hidden from your pings and chat.'}
              </p>
            </div>
          </div>
          <span className="text-xs font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
            {blocks.length}
          </span>
        </div>

        {blocks.length === 0 ? (
          <div className="bg-slate-950/70 p-3 rounded-2xl border border-slate-800 text-center">
            <p className="text-xs text-slate-400">
              {lang === 'pl' ? 'Brak zablokowanych użytkowników.' : 'No blocked users.'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {blocks.map((b) => {
              const user = b.user;
              return (
                <div
                  key={b.user.id}
                  className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2">
                    <UserAvatar name={user.name} src={user.avatar} className="w-7 h-7 rounded-full text-[10px]" />
                    <div>
                      <span className="font-bold text-white block">{user.name}</span>
                      {user.bio && <span className="text-[10px] text-slate-400">{user.bio}</span>}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleUnblockUser(user.id)}
                    className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-2.5 py-1 rounded-lg border border-slate-700 transition cursor-pointer"
                  >
                    {lang === 'pl' ? 'Odblokuj' : 'Unblock'}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Demo Profile Switcher */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-4 space-y-3">
        <div className="flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-emerald-400" />
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              {t.testPersonasTitle}
            </h3>
            <p className="text-[11px] text-slate-400">{t.testPersonasDesc}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2">
          {allUsers.map((u) => {
            const isSelected = u.id === currentUser.id;
            return (
              <button
                key={u.id}
                onClick={() => onSwitchUser(u.id)}
                className={`p-3 rounded-2xl border text-left flex items-center justify-between transition cursor-pointer ${
                  isSelected
                    ? 'bg-emerald-500/10 border-emerald-500/50 shadow-md'
                    : 'bg-slate-950 hover:bg-slate-800/80 border-slate-800'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <UserAvatar name={u.name} src={u.avatar} className="w-9 h-9 rounded-full text-xs" />
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-white">{u.name}</span>
                      <span className="text-[10px] text-slate-400">
                        ({u.trust_tier === 'Gold' ? (lang === 'pl' ? 'Złoty' : 'Gold') : u.trust_tier === 'Silver' ? (lang === 'pl' ? 'Srebrny' : 'Silver') : (lang === 'pl' ? 'Brązowy' : 'Bronze')}) • {u.city || 'Katowice'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {u.instagram_handle && (
                        <span className="text-[9px] text-rose-400 font-semibold bg-rose-500/10 px-1 rounded">
                          IG: {u.instagram_handle}
                        </span>
                      )}
                      {u.linkedin_handle && (
                        <span className="text-[9px] text-blue-400 font-semibold bg-blue-500/10 px-1 rounded">
                          in: {u.linkedin_handle}
                        </span>
                      )}
                      {u.tiktok_handle && (
                        <span className="text-[9px] text-cyan-400 font-semibold bg-cyan-500/10 px-1 rounded">
                          TikTok: {u.tiktok_handle}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className={`text-[11px] font-bold ${
                    (u.manner_temperature || 36.5) >= 38.0 ? 'text-amber-400' : 'text-emerald-400'
                  }`}>
                    {(u.manner_temperature || 36.5).toFixed(1)}°C
                  </span>
                  {isSelected && (
                    <span className="text-[10px] bg-emerald-500 text-slate-950 font-bold px-2 py-0.5 rounded-full">
                      {lang === 'pl' ? 'Aktywny' : 'Active'}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Actual completed outing count; no inferred impact or safety-rate claims. */}
      {stats && (
        <div className="bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border border-slate-800 rounded-3xl p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              {lang === 'pl' ? 'Aktywność CartMate' : 'CartMate activity'}
            </h3>
          </div>

          <div className="grid grid-cols-1 gap-2 text-xs">
            <div className="bg-slate-950/80 p-2.5 rounded-xl border border-slate-800">
              <span className="text-slate-400 block text-[10px]">{lang === 'pl' ? 'Ukończone wyjścia' : 'Completed outings'}</span>
              <span className="text-sm font-bold text-white">{stats.completed_outings_total.toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}

      {/* Social Media Connect Modal */}
      {import.meta.env.DEV && socialModalProvider && (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-indigo-500/60 w-full max-w-sm rounded-3xl p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Link2 className="w-4 h-4 text-indigo-400" />
                <span>{t.socialModalTitle}</span>
              </h3>
              <button
                onClick={() => setSocialModalProvider(null)}
                className="text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-300">
              {t.socialModalDesc}
            </p>

            <form onSubmit={handleConfirmConnect} className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  {t.socialHandleLabel} ({socialModalProvider.toUpperCase()})
                </label>
                <input
                  type="text"
                  required
                  value={socialInputHandle}
                  onChange={(e) => setSocialInputHandle(e.target.value)}
                  placeholder={t.socialHandlePlaceholder}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="bg-indigo-950/40 p-2.5 rounded-xl border border-indigo-500/30 text-[11px] text-indigo-200">
                {lang === 'pl'
                  ? 'Tryb demonstracyjny: wpisanie identyfikatora nie łączy konta przez OAuth ani nie potwierdza tożsamości.'
                  : 'Demo mode: entering a handle does not connect through OAuth or verify identity.'}
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSocialModalProvider(null)}
                  className="flex-1 py-2 rounded-xl border border-slate-700 text-slate-300 text-xs font-semibold hover:bg-slate-800 cursor-pointer"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={isProcessingSocial}
                  className="flex-1 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-md cursor-pointer"
                >
                  {isProcessingSocial ? '...' : t.socialConfirmConnect}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
