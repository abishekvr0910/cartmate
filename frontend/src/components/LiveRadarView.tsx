import React, { useState } from 'react';
import {
  Clock,
  MapPin,
  ShieldCheck,
  Award,
  Shield,
  Users,
  Lock,
  Flame,
  Sparkles,
  X,
  MessageCircle,
  Hand,
  UserPlus,
} from 'lucide-react';
import type { JoinRequest, LivePing, User } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';
import { OpenNeighborhoodMap } from './OpenNeighborhoodMap';
import { INTENTS } from '../constants/intents';
import { ACTIVITIES, activityEmoji, activityLabel } from '../constants/activities';
import { PeopleNearbyCard } from './PeopleNearbyCard';
import { SpotVotingWidget } from './SpotVotingWidget';
import { UserAvatar } from './UserAvatar';
import { fetchPingRequests, waveAtPing } from '../api';

interface LiveRadarViewProps {
  currentUser: User;
  pings: LivePing[];
  cityName?: string;
  lang: Language;
  onRefresh: () => void;
  onJoinPing: (pingId: string, message: string) => Promise<void>;
  onAcceptRequest: (pingId: string, reqId: string) => Promise<void>;
  onViewTrip: () => void;
  onOpenCreatePing: () => void;
}

const LiveRadarViewComponent: React.FC<LiveRadarViewProps> = ({
  currentUser,
  pings,
  cityName = 'Katowice',
  lang,
  onJoinPing,
  onAcceptRequest,
  onViewTrip,
  onOpenCreatePing,
}) => {
  const t = translations[lang] || translations.pl;
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedIntentId, setSelectedIntentId] = useState<string>('all');
  const [showIntentFilters, setShowIntentFilters] = useState(false);
  const [safeHavenOnly, setSafeHavenOnly] = useState<boolean>(currentUser.safe_haven_enabled);
  const [selectedPingId, setSelectedPingId] = useState<string | null>(null);

  // View Mode: Instagram Feed vs Dating App Deck vs GPS Map
  const [viewMode, setViewMode] = useState<'feed' | 'deck' | 'map'>('feed');
  const [deckIndex, setDeckIndex] = useState<number>(0);

  // Full-screen Instagram Story modal state
  const [activeStoryPing, setActiveStoryPing] = useState<LivePing | null>(null);

  // Dating App Mutual Match celebration overlay state
  const [celebrationOuting, setCelebrationOuting] = useState<{
    hostName: string;
    destination: string;
    avatar: string;
  } | null>(null);

  // Join modal state
  const [activeJoinPing, setActiveJoinPing] = useState<LivePing | null>(null);
  const [joinMessage, setJoinMessage] = useState<string>('');
  const [isSubmittingJoin, setIsSubmittingJoin] = useState(false);
  const [joinSuccess, setJoinSuccess] = useState(false);

  // Wave & Social action state
  const [wavedPingIds, setWavedPingIds] = useState<Record<string, boolean>>({});
  const [waveToast, setWaveToast] = useState<string | null>(null);

  // Host review requests modal state
  const [activeHostReviewPing, setActiveHostReviewPing] = useState<LivePing | null>(null);
  const [incomingRequests, setIncomingRequests] = useState<JoinRequest[]>([]);
  const [isLoadingRequests, setIsLoadingRequests] = useState(false);

  const categories = [
    { id: 'all', label: t.allPings },
    ...ACTIVITIES.map((activity) => ({ id: activity.id, label: t[activity.labelKey] })),
  ];

  const presets = lang === 'pl' ? [
    "Chętnie przejdę się razem po parku.",
    "Szukam towarzystwa do nauki w bibliotece.",
    "Może kawa i spokojna rozmowa?",
    "Chcę poćwiczyć, ale wolę iść z kimś.",
  ] : lang === 'uk' ? [
    "З радістю прогуляюся разом у парку.",
    "Шукаю компанію для навчання в бібліотеці.",
    "Може, кава і спокійна розмова?",
    "Хочу потренуватися, але краще разом.",
  ] : lang === 'ru' ? [
    "С удовольствием прогуляюсь вместе по парку.",
    "Ищу компанию для учёбы в библиотеке.",
    "Может, кофе и спокойный разговор?",
    "Хочу потренироваться, но лучше вместе.",
  ] : [
    "Would love company for a walk in the park.",
    "Anyone up for a library study session?",
    "How about coffee and a relaxed chat?",
    "Heading to a workout; company would be nice.",
  ];

  // Filter pings by category, SafeHaven, and shared intent
  const filteredPings = pings.filter((ping) => {
    if (selectedCategory !== 'all' && ping.category !== selectedCategory) return false;
    if (safeHavenOnly && !ping.women_only) return false;
    if (selectedIntentId !== 'all') {
      const intent = INTENTS.find((i) => i.id === selectedIntentId);
      if (intent) {
        const pingTags = (ping.intent_tags || []).map((t) => t.toLowerCase());
        const matchesTag = intent.tags.some((tag) => pingTags.some((pt) => pt.includes(tag.toLowerCase())));
        const matchesCategory = intent.categories.includes(ping.category);
        const matchesNotes = ping.notes?.toLowerCase().includes(intent.id.toLowerCase()) || false;
        if (!matchesTag && !matchesCategory && !matchesNotes) return false;
      }
    }
    return true;
  });

  const handleWave = async (ping: LivePing) => {
    if (wavedPingIds[ping.id]) return;
    try {
      await waveAtPing(ping.id);
      setWavedPingIds((prev) => ({ ...prev, [ping.id]: true }));
      const name = ping.host.name.split(' ')[0];
      setWaveToast(
        lang === 'pl'
          ? `Pomachano do ${name}! 👋`
          : lang === 'uk'
          ? `Ви помахали ${name}! 👋`
          : lang === 'ru'
          ? `Вы помахали ${name}! 👋`
          : `Waved at ${name}! 👋`
      );
    } catch (error) {
      console.warn('Wave dispatch error:', error);
      setWaveToast(lang === 'pl' ? 'Nie udało się pomachać. Spróbuj ponownie.' : 'Could not send your wave. Please retry.');
    }
    setTimeout(() => setWaveToast(null), 3000);
  };

  const handleAsk = (ping: LivePing) => {
    const name = ping.host.name.split(' ')[0];
    const defaultAskMsg =
      lang === 'pl'
        ? `Cześć ${name}, o której dokładnie będziesz na miejscu? Chętnie dołączę!`
        : lang === 'uk'
        ? `Привіт ${name}, о котрій годині плануєш бути на місці? Охоче приєднаюся!`
        : lang === 'ru'
        ? `Привет ${name}, во сколько точно будешь на месте? С удовольствием присоединюсь!`
        : `Hey ${name}, what time are you meeting there? Would love to join!`;
    setJoinMessage(defaultAskMsg);
    setActiveJoinPing(ping);
  };

  const handleOpenJoin = (ping: LivePing) => {
    setActiveJoinPing(ping);
    const greeting = lang === 'pl'
      ? `Cześć ${ping.host.name.split(' ')[0]}! Chętnie dołączę do Twojego wyjścia do ${ping.destination_name}.`
      : lang === 'uk'
      ? `Привіт ${ping.host.name.split(' ')[0]}! Залюбки приєднаюся до твого виходу в ${ping.destination_name}.`
      : lang === 'ru'
      ? `Привет ${ping.host.name.split(' ')[0]}! С удовольствием присоединюсь к твоему выходу в ${ping.destination_name}.`
      : `Hey ${ping.host.name.split(' ')[0]}! Would love to join your ${ping.destination_name} outing.`;
    setJoinMessage(greeting);
    setJoinSuccess(false);
  };

  const handleSubmitJoin = async () => {
    if (!activeJoinPing) return;
    setIsSubmittingJoin(true);
    try {
      await onJoinPing(activeJoinPing.id, joinMessage);
      setJoinSuccess(true);
      const hostFirstName = activeJoinPing.host.name.split(' ')[0];

      setTimeout(() => {
        setActiveJoinPing(null);
        setJoinSuccess(false);
        setWaveToast(
          lang === 'pl'
            ? `Wysłano prośbę o dołączenie do ${hostFirstName}! Czekaj na potwierdzenie.`
            : lang === 'uk'
            ? `Запит на приєднання надіслано до ${hostFirstName}! Очікуйте на підтвердження.`
            : lang === 'ru'
            ? `Запрос на присоединение отправлен ${hostFirstName}! Ожидайте подтверждения.`
            : `Join request sent to ${hostFirstName}! Waiting for confirmation.`
        );
        setTimeout(() => setWaveToast(null), 3500);
      }, 1200);
    } catch (err: any) {
      alert(err.message || 'Błąd wysyłania zgłoszenia');
    } finally {
      setIsSubmittingJoin(false);
    }
  };

  const handleOpenHostRequests = async (ping: LivePing) => {
    setActiveHostReviewPing(ping);
    setIsLoadingRequests(true);
    try {
      const requests = await fetchPingRequests(ping.id);
      setIncomingRequests(requests);
    } catch (e: any) {
      alert(e.message || 'Could not load join requests.');
    } finally {
      setIsLoadingRequests(false);
    }
  };

  const handleAcceptApplicant = async (reqId: string) => {
    if (!activeHostReviewPing) return;
    try {
      const applicant = incomingRequests.find((r) => r.id === reqId)?.applicant;
      await onAcceptRequest(activeHostReviewPing.id, reqId);
      if (applicant) {
        setCelebrationOuting({
          hostName: applicant.name,
          destination: activeHostReviewPing.destination_name,
          avatar: applicant.avatar,
        });
      }
      setActiveHostReviewPing(null);
    } catch (e: any) {
      alert(e.message || 'Błąd akceptacji');
    }
  };

  const formatDistance = (ping: LivePing) => {
    const km = ping.distance_km ?? (ping.distance_miles ? ping.distance_miles * 1.60934 : 0.5);
    if (lang === 'en') {
      const miles = km * 0.621371;
      return `${miles.toFixed(1)} mi`;
    }
    return `${km.toFixed(1)} km`;
  };

  const renderTierPill = (tier: string) => {
    switch (tier) {
      case 'Gold':
        return (
          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
            <Award className="w-3 h-3 text-amber-400" />
            {lang === 'pl' ? 'Złoty' : lang === 'uk' ? 'Золотий' : lang === 'ru' ? 'Золотой' : 'Gold'}
          </span>
        );
      case 'Silver':
        return (
          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
                    {lang === 'pl' ? 'ID zweryfikowane' : lang === 'uk' ? 'ID перевірено' : lang === 'ru' ? 'ID проверен' : 'ID verified'}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/40">
            <Shield className="w-3 h-3 text-blue-400" />
            {lang === 'pl' ? 'Brązowy' : lang === 'uk' ? 'Бронзовий' : lang === 'ru' ? 'Бронзовый' : 'Bronze'}
          </span>
        );
    }
  };

  // Active ping for Tinder/Hinge Deck Mode
  const activeDeckPing = filteredPings.length > 0 ? filteredPings[deckIndex % filteredPings.length] : null;

  return (
    <div className="p-4 space-y-4 max-w-5xl mx-auto pb-24">
      {/* Wave Toast Feedback */}
      {waveToast && (
        <div className="sticky top-2 z-50 px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-400 text-slate-950 font-bold rounded-2xl shadow-2xl flex items-center justify-center gap-2 text-xs border border-amber-300 animate-bounce">
          <span className="text-base">👋</span>
          <span>{waveToast}</span>
        </div>
      )}

      {/* Optional people preview; on phones, show actual outing cards first. */}
      <div className="hidden sm:block space-y-1.5">
        <div className="flex items-center justify-between px-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-rose-400" />
            <span>{t.storiesTitle}</span>
          </span>
          <span className="text-[10px] text-slate-500 font-medium">
            {filteredPings.length} {lang === 'pl' ? 'wyjść' : lang === 'uk' ? 'виходів' : lang === 'ru' ? 'встреч' : 'outings'}
          </span>
        </div>

        <div className="flex items-center gap-3 overflow-x-auto pb-2 scrollbar-none px-1">
          {/* Your Outing (+ Story) */}
          <button
            type="button"
            onClick={onOpenCreatePing}
            className="flex flex-col items-center gap-1.5 shrink-0 group cursor-pointer"
          >
            <div className="relative w-15 h-15 rounded-full p-0.5 border-2 border-dashed border-emerald-500/60 group-hover:border-emerald-400 transition-all flex items-center justify-center bg-slate-900">
              <UserAvatar name={currentUser.name} src={currentUser.avatar} className="w-13 h-13 rounded-full text-sm opacity-80 group-hover:opacity-100 transition" />
              <div className="absolute bottom-0 right-0 w-4.5 h-4.5 rounded-full bg-emerald-500 text-slate-950 font-bold flex items-center justify-center text-xs shadow-md">
                +
              </div>
            </div>
            <span className="text-[10px] font-semibold text-slate-300 max-w-[62px] truncate group-hover:text-emerald-400 transition">
              {currentUser.name.split(' ')[0]}
            </span>
          </button>

          {/* Neighbor Story Bubbles with Instagram Gradient Rings */}
          {filteredPings.map((ping) => {
            const minutesLeft = Math.max(1, Math.round(ping.remaining_seconds / 60));
            return (
              <button
                key={`story-${ping.id}`}
                type="button"
                onClick={() => setActiveStoryPing(ping)}
                className="flex flex-col items-center gap-1.5 shrink-0 group cursor-pointer"
              >
                <div className="relative p-0.5 rounded-full bg-gradient-to-tr from-amber-400 via-rose-500 to-purple-600 shadow-md group-hover:scale-105 transition-transform">
                  <div className="p-0.5 bg-[#0b0f19] rounded-full">
                    <UserAvatar name={ping.host.name} src={ping.host.avatar} className="w-13 h-13 rounded-full text-sm" />
                  </div>
                  {/* Category Emoji Badge */}
                  <div className="absolute -bottom-1 -right-1 text-xs px-1 py-0.2 rounded-full bg-slate-900 border border-slate-700 shadow">
                    {activityEmoji(ping.category)}
                  </div>
                </div>
                <div className="text-center">
                  <span className="text-[10px] font-bold text-white max-w-[64px] truncate block leading-tight">
                    {ping.host.name.split(' ')[0]}
                  </span>
                  <span className="text-[9px] text-amber-400 font-semibold">
                    {minutesLeft}m
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. VIEW MODE TOGGLE (Instagram Feed vs Dating Match Deck vs GPS Radar) */}
      <div className="flex rounded-xl bg-slate-900/90 p-1 border border-slate-800 gap-1 shadow-md">
        <button
          type="button"
          onClick={() => setViewMode('feed')}
          aria-label={t.viewModeFeed}
          className={`min-w-0 min-h-11 flex-1 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
            viewMode === 'feed'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>📱</span>
          <span>{t.viewModeFeed}</span>
        </button>
        <button
          type="button"
          onClick={() => setViewMode('deck')}
          aria-label={t.viewModeDeck}
          className={`min-w-0 min-h-11 flex-1 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
            viewMode === 'deck'
              ? 'bg-gradient-to-r from-rose-500/25 to-amber-500/25 text-rose-300 shadow-sm border border-rose-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>🔥</span>
          <span>{t.viewModeDeck}</span>
        </button>
        <button
          type="button"
          onClick={() => setViewMode('map')}
          aria-label={t.viewModeMap}
          className={`min-w-0 min-h-11 flex-1 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
            viewMode === 'map'
              ? 'bg-emerald-500/20 text-emerald-300 shadow-sm border border-emerald-500/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>🗺️</span>
          <span>{t.viewModeMap}</span>
        </button>
      </div>

      {/* 3. CATEGORY PILL FILTER */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none items-center">
        {currentUser.gender === 'female' && (
          <button
            type="button"
            onClick={() => setSafeHavenOnly(!safeHavenOnly)}
            className={`px-3 py-1.5 rounded-xl text-xs whitespace-nowrap transition cursor-pointer font-bold flex items-center gap-1.5 border ${
              safeHavenOnly
                ? 'bg-purple-600/30 text-purple-200 border-purple-500/60 shadow-md shadow-purple-500/10'
                : 'bg-slate-800/80 text-slate-400 hover:bg-slate-700 border-slate-700/60'
            }`}
          >
            <Lock className="w-3.5 h-3.5 text-purple-400" />
            <span>{t.safeHavenFilter}</span>
          </button>
        )}
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1.5 rounded-xl text-xs whitespace-nowrap transition cursor-pointer font-medium ${
              selectedCategory === cat.id
                ? 'bg-emerald-500 text-slate-950 font-bold shadow-md shadow-emerald-500/20'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 border border-slate-700/60'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* 3B. SHARED INTENT FILTER PILLS (Anti-Loneliness & Purpose Matching) */}
      <div className="space-y-1.5 pt-1">
        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
          <button
            type="button"
            onClick={() => setShowIntentFilters((open) => !open)}
            aria-expanded={showIntentFilters}
            aria-controls="intent-filter-options"
            className="min-h-11 font-semibold text-slate-300 flex items-center gap-1.5"
          >
            <span>🎯</span>
            <span>{lang === 'pl' ? 'Cel:' : lang === 'uk' ? 'Мета:' : lang === 'ru' ? 'Цель:' : 'Purpose:'}</span>
            <span className="text-amber-300">{selectedIntentId === 'all' ? t.intentAll : INTENTS.find((intent) => intent.id === selectedIntentId)?.labels[lang]}</span>
            <span aria-hidden="true">{showIntentFilters ? '▴' : '▾'}</span>
          </button>
          {selectedIntentId !== 'all' && (
            <button
              onClick={() => setSelectedIntentId('all')}
              className="text-amber-400 hover:text-amber-300 text-[10px] font-bold underline cursor-pointer"
            >
              {lang === 'pl' ? 'Pokaż wszystkie' : 'Show all'}
            </button>
          )}
        </div>
        {showIntentFilters && <div id="intent-filter-options" className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none items-center">
          <button
            type="button"
            onClick={() => setSelectedIntentId('all')}
            className={`px-3 py-1.5 rounded-xl text-xs whitespace-nowrap transition cursor-pointer font-bold flex items-center gap-1 ${
              selectedIntentId === 'all'
                ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 border border-slate-700/60'
            }`}
          >
            <span>✨</span>
            <span>{t.intentAll}</span>
          </button>
          {INTENTS.map((intent) => {
            const count = pings.filter((p) => {
              const pingTags = (p.intent_tags || []).map((t) => t.toLowerCase());
              const matchesTag = intent.tags.some((tag) => pingTags.some((pt) => pt.includes(tag.toLowerCase())));
              const matchesCategory = intent.categories.includes(p.category);
              return matchesTag || matchesCategory;
            }).length;

            return (
              <button
                key={intent.id}
                type="button"
                onClick={() => setSelectedIntentId(selectedIntentId === intent.id ? 'all' : intent.id)}
                className={`px-3 py-1.5 rounded-xl text-xs whitespace-nowrap transition cursor-pointer font-medium flex items-center gap-1.5 ${
                  selectedIntentId === intent.id
                    ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 border border-slate-700/60'
                }`}
              >
                <span>{intent.emoji}</span>
                <span>{intent.labels[lang]}</span>
                {count > 0 && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    selectedIntentId === intent.id ? 'bg-slate-950/20 text-slate-950' : 'bg-slate-700 text-slate-300'
                  }`}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>}
      </div>

      {/* 4A. LIVING NEIGHBORHOOD MAP VIEW */}
      {viewMode === 'map' && (
        <div className="space-y-3">
          <OpenNeighborhoodMap
            pings={filteredPings}
            cityName={cityName}
            selectedPingId={selectedPingId}
            onSelectPing={(pingId) => {
              setSelectedPingId(pingId);
              setViewMode('feed');
              setTimeout(() => {
                const el = document.getElementById(`ping-${pingId}`);
                el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }, 100);
            }}
            lang={lang}
          />

          {/* Living Community List below Map */}
          <PeopleNearbyCard
            pings={filteredPings}
            currentUser={currentUser}
            lang={lang}
            onSelectPing={(pingId) => {
              setSelectedPingId(pingId);
              setViewMode('feed');
              setTimeout(() => {
                const el = document.getElementById(`ping-${pingId}`);
                el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }, 150);
            }}
            onWave={handleWave}
            onJoin={handleOpenJoin}
            onAsk={handleAsk}
            wavedPingIds={wavedPingIds}
          />

          {/* Crowdsourced Neighborhood Spot Voting & Group Outing Formation */}
          <SpotVotingWidget
            currentUser={currentUser}
            cityName={cityName}
            lang={lang}
            onJoinCrew={(spot) => {
              setWaveToast(
                lang === 'pl'
                  ? `Dołączono do ekipy wyjścia do ${spot.name}! 🎉`
                  : `Joined the crew heading to ${spot.name}! 🎉`
              );
              setTimeout(() => setWaveToast(null), 3500);
            }}
          />
        </div>
      )}

      {/* 4B. DATING APP MATCH DECK MODE (Tinder / Hinge Style) */}
      {viewMode === 'deck' && (
        <div className="space-y-4">
          {!activeDeckPing ? (
            <div className="text-center py-16 px-4 bg-slate-900/60 rounded-3xl border border-slate-800 space-y-3">
              <Users className="w-12 h-12 text-slate-600 mx-auto" />
              <p className="text-sm text-slate-400 font-medium">{t.noPings}</p>
              <button
                onClick={onOpenCreatePing}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-bold underline cursor-pointer"
              >
                {t.firstToPost}
              </button>
            </div>
          ) : (
            <div className="relative bg-gradient-to-b from-slate-900 via-slate-900/95 to-slate-950 rounded-3xl border border-slate-700/80 p-5 shadow-2xl space-y-4 overflow-hidden">
              {/* Card Deck Counter */}
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1">
                  <Flame className="w-3.5 h-3.5 fill-rose-400 text-rose-400" />
                  <span>{lang === 'pl' ? 'Jedno wyjście na raz' : 'One outing at a time'}</span>
                </span>
                <span className="bg-slate-800 px-2 py-0.5 rounded-full text-[11px] font-semibold">
                  {(deckIndex % filteredPings.length) + 1} / {filteredPings.length}
                </span>
              </div>

              {/* Host Hero Cover & Vibe Compatibility */}
              <div className="relative rounded-2xl overflow-hidden aspect-[4/3] bg-slate-950 border border-slate-800">
                <UserAvatar name={activeDeckPing.host.name} src={activeDeckPing.host.avatar} className="w-full h-full text-6xl" />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent" />
                
                {/* Vibe Match Badge (Dating style) */}
                <div className="absolute top-3 left-3 bg-rose-600/90 backdrop-blur-md text-white font-extrabold text-[11px] px-2.5 py-1 rounded-full shadow-lg flex items-center gap-1 border border-rose-400/40">
                  <Flame className="w-3.5 h-3.5 fill-white" />
                  <span>{lang === 'pl' ? 'Pomysł na wspólne wyjście' : 'Shared outing idea'}</span>
                </div>

                {/* TTL Pill */}
                <div className="absolute top-3 right-3 bg-amber-500/90 text-slate-950 font-black text-xs px-2.5 py-1 rounded-full shadow-md flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-950" />
                  <span>{Math.max(1, Math.round(activeDeckPing.remaining_seconds / 60))}m {t.minutesLeft}</span>
                </div>

                {/* Bottom Overlay Info */}
                <div className="absolute bottom-3 left-3 right-3 text-white space-y-0.5">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-black tracking-tight">{activeDeckPing.host.name}</h3>
                    {renderTierPill(activeDeckPing.host.trust_tier)}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-slate-300">
                    <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span className="font-semibold">{activeDeckPing.destination_name}</span>
                    <span className="text-slate-400">• {formatDistance(activeDeckPing)} {t.away}</span>
                  </div>
                </div>
              </div>

              {/* Hinge-style Prompt 1: Destination & Goal */}
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-3.5 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-teal-400">
                  📍 {lang === 'pl' ? 'Gdzie idziemy:' : lang === 'uk' ? 'Куди вирушаємо:' : lang === 'ru' ? 'Куда направляемся:' : 'Where we are heading:'}
                </span>
                <p className="text-sm font-bold text-white">
                  {activeDeckPing.destination_name} ({activeDeckPing.address})
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {activeDeckPing.intent_tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-teal-500/10 text-teal-300 border border-teal-500/20"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Hinge-style Prompt 2: Host Voice */}
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-3.5 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                  💬 {t.whyGoing}
                </span>
                <p className="text-xs text-slate-200 italic leading-relaxed">
                  "{activeDeckPing.notes || 'Szukam towarzysza na wspólne wyjście!'}"
                </p>
              </div>

              {/* Review claims appear only after a participant has reviewed an outing. */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-3 text-xs text-slate-300">
                {activeDeckPing.host.reviews_count > 0 ? (
                  <span>⭐ {activeDeckPing.host.rating.toFixed(1)} · {activeDeckPing.host.reviews_count} {lang === 'pl' ? 'opinii uczestników' : 'participant reviews'}</span>
                ) : (
                  <span>{lang === 'pl' ? 'Nowa osoba · brak ocen po spotkaniu' : 'New member · no post-outing reviews yet'}</span>
                )}
              </div>

              {/* Explicit actions: browse, wave, or request to join. */}
              <div className="flex items-center justify-center gap-4 pt-2">
                {/* Pass button */}
                <button
                  type="button"
                  onClick={() => setDeckIndex((prev) => prev + 1)}
                  className="w-13 h-13 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 flex items-center justify-center shadow-lg transition-transform hover:scale-110 cursor-pointer"
                  title={t.deckNext}
                >
                  <X className="w-6 h-6" />
                </button>

                {/* Wave Button */}
                <button
                  type="button"
                  onClick={() => handleWave(activeDeckPing)}
                  className={`w-11 h-11 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110 cursor-pointer ${
                    wavedPingIds[activeDeckPing.id]
                      ? 'bg-amber-500 text-slate-950 font-bold border border-amber-400'
                      : 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40'
                  }`}
                  title={t.actionWave}
                >
                  <Hand className="w-5 h-5" />
                </button>

                {/* Request to join; host approval is still required. */}
                <button
                  type="button"
                  onClick={() => handleOpenJoin(activeDeckPing)}
                  className="px-6 h-13 rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 text-slate-950 font-black text-sm flex items-center gap-2 shadow-xl shadow-emerald-500/25 hover:scale-105 transition-transform cursor-pointer"
                >
                  <UserPlus className="w-5 h-5" />
                  <span>{t.deckMatch}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4C. INSTAGRAM FEED VIEW MODE */}
      {viewMode === 'feed' && (
        <div className="space-y-4">
          {filteredPings.length === 0 ? (
            <div className="text-center py-12 px-4 bg-slate-900/40 rounded-2xl border border-slate-800/60 space-y-3">
              <Users className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-sm text-slate-400 font-medium">{t.noPings}</p>
              <button
                onClick={onOpenCreatePing}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-bold underline cursor-pointer"
              >
                {t.firstToPost}
              </button>
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2 items-start">
            {filteredPings.map((ping) => {
              const isHost = ping.host.id === currentUser.id;
              const minutesLeft = Math.max(1, Math.round(ping.remaining_seconds / 60));
              const isSelected = selectedPingId === ping.id;

              return (
                <div
                  id={`ping-${ping.id}`}
                  key={ping.id}
                  className={`bg-slate-900/90 border rounded-3xl transition-all duration-300 shadow-xl overflow-hidden space-y-0 ${
                    isSelected
                      ? 'border-amber-400/90 ring-2 ring-amber-400/40 shadow-amber-500/10'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  {/* INSTAGRAM POST HEADER */}
                  <div className="p-3.5 flex items-center justify-between border-b border-slate-800/60 bg-slate-950/40">
                    <div className="flex items-center gap-2.5">
                      {/* Avatar with Story Ring */}
                      <button
                        type="button"
                        onClick={() => setActiveStoryPing(ping)}
                        className="p-0.5 rounded-full bg-gradient-to-tr from-amber-400 via-rose-500 to-purple-600 cursor-pointer"
                      >
                        <UserAvatar name={ping.host.name} src={ping.host.avatar} className="w-9 h-9 rounded-full border-2 border-slate-950 text-xs" />
                      </button>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-black text-white hover:underline cursor-pointer">
                            {ping.host.name}
                          </span>
                          {renderTierPill(ping.host.trust_tier)}
                        </div>
                        <div className="flex items-center gap-1 text-[11px] text-slate-400">
                          <MapPin className="w-3 h-3 text-emerald-400 shrink-0" />
                          <span className="font-semibold text-slate-300">{ping.destination_name}</span>
                          <span className="text-slate-600">•</span>
                          <span>{formatDistance(ping)} {t.away}</span>
                        </div>
                      </div>
                    </div>

                    {/* TTL Decay Pill */}
                    <div className="flex items-center gap-1 bg-amber-500/10 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full text-xs font-bold shrink-0">
                      <Clock className="w-3 h-3 text-amber-400" />
                      <span>{minutesLeft}m</span>
                    </div>
                  </div>

                  {/* VISUAL VENUE HERO BANNER (Instagram Card Media) */}
                  <div className="relative bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 border-b border-slate-800/60">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                          {activityLabel(ping.category, t)}
                        </span>
                        <h4 className="text-base font-bold text-white tracking-tight pt-1">
                          {ping.destination_name}
                        </h4>
                        <p className="text-xs text-slate-400">{ping.address}</p>
                      </div>

                    </div>

                    {/* Intent Tag Chips */}
                    <div className="flex flex-wrap gap-1.5 pt-3">
                      {ping.intent_tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-800/90 text-teal-300 border border-slate-700/60"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>

                    {/* Host Note / Quote (Hinge/Instagram prompt style) */}
                    {ping.notes && (
                      <p className="text-xs text-slate-200 bg-slate-900/90 p-2.5 rounded-xl border border-slate-700/60 mt-3 italic leading-relaxed">
                        "{ping.notes}"
                      </p>
                    )}
                  </div>

                  {/* Only server-backed actions appear on an outing card. */}
                  <div className="px-3.5 py-3 border-b border-slate-800/40">
                    <div className="flex items-center justify-end gap-2">
                      {isHost ? (
                        <button
                          onClick={() => handleOpenHostRequests(ping)}
                          className="min-h-11 bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 border border-teal-500/40 text-xs font-bold px-3 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-1"
                        >
                          <Users className="w-3.5 h-3.5" />
                          <span>{t.requests}</span>
                        </button>
                      ) : (
                        <div className="flex w-full items-center gap-1.5">
                          {/* Lightweight Wave */}
                          <button
                            type="button"
                            onClick={() => handleWave(ping)}
                            className={`min-h-11 flex-1 justify-center px-2.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1 transition cursor-pointer active:scale-95 ${
                              wavedPingIds[ping.id]
                                ? 'bg-amber-500 text-slate-950 font-bold shadow-sm'
                                : 'bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30'
                            }`}
                            title="Pomachaj"
                          >
                            <Hand className="w-3.5 h-3.5" />
                            <span>{wavedPingIds[ping.id] ? '👋' : t.actionWave}</span>
                          </button>

                          {/* Quick Ask */}
                          <button
                            type="button"
                            onClick={() => handleAsk(ping)}
                            className="min-h-11 flex-1 justify-center px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer active:scale-95"
                            title="Zapytaj"
                          >
                            <MessageCircle className="w-3.5 h-3.5 text-slate-300" />
                            <span>{t.actionAsk}</span>
                          </button>

                          {/* Join Outing CTA */}
                          <button
                            type="button"
                            onClick={() => handleOpenJoin(ping)}
                            className="min-h-11 flex-[1.3] justify-center bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 text-xs font-bold px-3 py-1.5 rounded-xl transition shadow-md shadow-emerald-500/20 flex items-center gap-1 cursor-pointer active:scale-95"
                          >
                            <UserPlus className="w-3.5 h-3.5 text-slate-950" />
                            <span>{t.actionJoin}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="px-3.5 py-2 bg-slate-950/60 flex items-center justify-between gap-2 text-[11px] text-slate-400">
                    <span>{ping.host.trips_completed} {lang === 'pl' ? 'ukończonych wyjść' : 'completed outings'}</span>
                    <span>
                      {ping.host.reviews_count > 0
                        ? `⭐ ${ping.host.rating.toFixed(1)} (${ping.host.reviews_count})`
                        : lang === 'pl' ? 'Bez ocen po spotkaniu' : 'No post-outing reviews'}
                    </span>
                  </div>
                </div>
              );
            })}
            </div>
          )}

          {/* Secondary discovery follows real person-to-person outings. */}
          <SpotVotingWidget
            currentUser={currentUser}
            cityName={cityName}
            lang={lang}
            onJoinCrew={(spot) => {
              setWaveToast(
                lang === 'pl'
                  ? `Dołączono do ekipy wyjścia do ${spot.name}! 🎉`
                  : `Joined the crew heading to ${spot.name}! 🎉`
              );
              setTimeout(() => setWaveToast(null), 3500);
            }}
          />
        </div>
      )}

      {/* 5. FULL-SCREEN INSTAGRAM STORIES VIEWER MODAL */}
      {activeStoryPing && (
        <div
          className="fixed inset-0 z-50 bg-black/95 backdrop-blur-md flex items-center justify-center p-3 sm:p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Story Viewer"
        >
          <div className="bg-[#0b0f19] border border-slate-700 w-full max-w-sm rounded-3xl overflow-hidden shadow-2xl flex flex-col relative aspect-[9/16] max-h-[85vh]">
            {/* Top Stories Progress Bar */}
            <div className="p-3 pb-1 flex gap-1 z-20">
              <div className="h-1 bg-white/30 rounded-full flex-1 overflow-hidden">
                <div className="h-full bg-white animate-[pulse_3s_ease-in-out_infinite] w-full" />
              </div>
            </div>

            {/* Header: Host info & Close */}
            <div className="px-3 py-2 flex items-center justify-between z-20">
              <div className="flex items-center gap-2">
                <UserAvatar name={activeStoryPing.host.name} src={activeStoryPing.host.avatar} className="w-8 h-8 rounded-full border border-emerald-400 text-xs" />
                <div>
                  <span className="text-xs font-bold text-white block leading-tight">
                    {activeStoryPing.host.name}
                  </span>
                  <span className="text-[10px] text-emerald-400">
                    {activeStoryPing.destination_name}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setActiveStoryPing(null)}
                aria-label="Zamknij relację"
                className="flex min-h-10 min-w-10 items-center justify-center text-slate-400 hover:text-white rounded-full bg-slate-800/80 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Story Content Area */}
            <div className="flex-1 p-5 flex flex-col justify-between text-center relative z-10">
              <div className="space-y-4 my-auto">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-400 to-rose-500 mx-auto flex items-center justify-center text-3xl shadow-xl shadow-rose-500/20">
                  {activityEmoji(activeStoryPing.category)}
                </div>

                <div className="space-y-1">
                  <h3 className="text-xl font-black text-white tracking-tight">
                    {activeStoryPing.destination_name}
                  </h3>
                  <p className="text-xs text-slate-300">{activeStoryPing.address}</p>
                </div>

                <p className="text-sm text-slate-200 bg-slate-900/90 border border-slate-800 p-4 rounded-2xl italic leading-relaxed shadow-lg">
                  "{activeStoryPing.notes || 'Idę za chwilę, zapraszam sąsiadów do wspólnego wyjścia!'}"
                </p>

                <div className="flex flex-wrap justify-center gap-1.5">
                  {activeStoryPing.intent_tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-[11px] font-bold px-2.5 py-1 rounded-lg bg-teal-500/20 text-teal-300 border border-teal-500/30"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Bottom Quick Reply / Join Button */}
              <div className="pt-4 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const ping = activeStoryPing;
                    setActiveStoryPing(null);
                    handleOpenJoin(ping);
                  }}
                  className="flex-1 py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-xl shadow-emerald-500/30 transition cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span>{t.joinRun}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6. MUTUAL MATCH CELEBRATION OVERLAY ("It's an Outing! 🎉") */}
      {celebrationOuting && (
        <div
          className="app-dialog fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center overflow-y-auto p-3 sm:p-4 animate-fade-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="celebration-title"
        >
          <div className="my-auto max-h-[calc(100dvh-1.5rem)] overflow-y-auto bg-gradient-to-b from-[#0f172a] to-[#070a13] border-2 border-emerald-500/60 w-full max-w-sm rounded-3xl p-6 text-center space-y-4 shadow-2xl relative">
            <div className="w-14 h-14 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center mx-auto text-2xl animate-bounce">
              🎉
            </div>

            <div className="space-y-1">
              <h3 id="celebration-title" className="text-xl font-black text-white tracking-tight">
                {t.itsAnOuting}
              </h3>
              <p className="text-xs text-slate-300">
                {t.celebrateSub}
              </p>
            </div>

            {/* Interconnected Avatars */}
            <div className="flex items-center justify-center gap-3 py-2">
              <UserAvatar name={currentUser.name} src={currentUser.avatar} className="w-14 h-14 rounded-full border-2 border-emerald-400 shadow-lg text-sm" />
              <span className="text-emerald-400 font-black text-lg">⚡</span>
              <UserAvatar name={celebrationOuting.hostName} src={celebrationOuting.avatar} className="w-14 h-14 rounded-full border-2 border-emerald-400 shadow-lg text-sm" />
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-slate-300">
              <span className="font-bold text-white block mb-0.5">{celebrationOuting.destination}</span>
              <span className="text-[11px] text-emerald-400">
                {lang === 'pl' ? 'Wspólne wyjście z:' : lang === 'uk' ? 'Спільний вихід із:' : lang === 'ru' ? 'Совместный выход с:' : 'Companion:'} {celebrationOuting.hostName}
              </span>
            </div>

            <div className="pt-2 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => {
                  setCelebrationOuting(null);
                  onViewTrip();
                }}
                className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs py-3 rounded-xl transition shadow-lg shadow-emerald-500/20 cursor-pointer"
              >
                {t.openChatCoord}
              </button>
              <button
                type="button"
                onClick={() => setCelebrationOuting(null)}
                className="text-xs text-slate-400 hover:text-slate-300 py-1 cursor-pointer"
              >
                {t.cancel}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. JOIN REQUEST MODAL */}
      {activeJoinPing && (
        <div
          className="app-dialog fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center overflow-y-auto p-3 sm:p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="join-request-modal-title"
        >
          <div className="my-auto max-h-[calc(100dvh-1.5rem)] overflow-y-auto bg-[#0f172a] border border-slate-700 w-full max-w-md rounded-2xl p-4 sm:p-5 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                  {t.requestModalTitle}
                </span>
                <h3 id="join-request-modal-title" className="text-lg font-bold text-white">{activeJoinPing.destination_name}</h3>
                <p className="text-xs text-slate-400">{activeJoinPing.address}</p>
              </div>
              <button
                onClick={() => setActiveJoinPing(null)}
                aria-label="Zamknij"
                className="flex min-h-10 min-w-10 items-center justify-center text-slate-400 hover:text-white text-lg font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Quick message presets */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 block">{t.quickNoteLabel}</label>
              <div className="flex flex-wrap gap-1.5">
                {presets.map((msg) => (
                  <button
                    key={msg}
                    type="button"
                    onClick={() => setJoinMessage(msg)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    {msg}
                  </button>
                ))}
              </div>
            </div>

            <textarea
              rows={3}
              value={joinMessage}
              onChange={(e) => setJoinMessage(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />

            <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl space-y-1 text-xs text-slate-400">
              <span className="font-bold text-slate-300 block">{t.safetyTipTitle}</span>
              <p>{t.safetyTipText}</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setActiveJoinPing(null)}
                className="flex-1 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-bold hover:bg-slate-800 transition cursor-pointer"
              >
                {t.cancel}
              </button>
              <button
                onClick={handleSubmitJoin}
                disabled={isSubmittingJoin || joinSuccess}
                className="flex-1 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-lg shadow-emerald-500/20 transition cursor-pointer disabled:opacity-50"
              >
                {joinSuccess ? t.sent : isSubmittingJoin ? t.sending : t.sendRequest}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. HOST REVIEW REQUESTS MODAL */}
      {activeHostReviewPing && (
        <div
          className="app-dialog fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center overflow-y-auto p-3 sm:p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="host-review-modal-title"
        >
          <div className="my-auto max-h-[calc(100dvh-1.5rem)] overflow-y-auto bg-[#0f172a] border border-slate-700 w-full max-w-md rounded-2xl p-4 sm:p-5 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-bold text-teal-400 uppercase tracking-wider">
                  {t.reviewApplicants}
                </span>
                <h3 id="host-review-modal-title" className="text-lg font-bold text-white">
                  {activeHostReviewPing.destination_name}
                </h3>
              </div>
              <button
                onClick={() => setActiveHostReviewPing(null)}
                aria-label="Zamknij"
                className="flex min-h-10 min-w-10 items-center justify-center text-slate-400 hover:text-white text-lg font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            {isLoadingRequests ? (
              <p className="text-xs text-slate-400 text-center py-6">
                {lang === 'pl' ? 'Wczytywanie kandydatów...' : 'Loading applicant profiles...'}
              </p>
            ) : incomingRequests.length === 0 ? (
              <div className="text-center py-6 space-y-2">
                <Users className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-xs text-slate-400">{t.noApplicantsYet}</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-72 overflow-y-auto">
                {incomingRequests.map((req) => (
                  <div
                    key={req.id}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <UserAvatar name={req.applicant.name} src={req.applicant.avatar} className="w-8 h-8 rounded-full text-xs" />
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-bold text-white">{req.applicant.name}</span>
                            {renderTierPill(req.applicant.trust_tier)}
                          </div>
                          <span className="text-[10px] text-slate-400">
                            {req.applicant.trips_completed} {lang === 'pl' ? 'ukończonych wyjść' : 'completed outings'}
                            {req.applicant.reviews_count > 0 && ` · ⭐ ${req.applicant.rating.toFixed(1)} (${req.applicant.reviews_count})`}
                          </span>
                        </div>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 bg-slate-950/80 p-2 rounded-lg italic">
                      "{req.message}"
                    </p>

                    <button
                      onClick={() => handleAcceptApplicant(req.id)}
                      className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 rounded-lg transition shadow-md shadow-emerald-500/20 cursor-pointer"
                    >
                      {t.acceptCompanion}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export const LiveRadarView = React.memo(LiveRadarViewComponent);
