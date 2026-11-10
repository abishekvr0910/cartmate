import React, { useState, useEffect, useCallback } from 'react';
import type { Pod, PodMessage } from '../types';
import type { Language } from '../locales';
import { fetchPodFeed, joinPod, leavePod, fetchPodMessages, sendPodMessage } from '../api';
import { realtime } from '../realtime/socket';
import { useDialogFocus } from '../hooks/useDialogFocus';
import {
  Users,
  MapPin,
  Clock,
  MessageSquare,
  CheckCircle2,
  AlertCircle,
  X,
  Send,
  Sparkles,
  ShieldCheck,
  ChevronRight,
  Calendar,
  Compass,
} from 'lucide-react';

interface PodFeedProps {
  token: string | null;
  currentUserId?: string | null;
  onRequireAuth?: () => void;
  lang?: Language;
}

interface PodMemberShiftEvent {
  pod_id?: number;
  user_id?: string;
  user_name?: string;
  confirmed_count?: number;
  status?: Pod['status'];
}

function unwrapPodShiftEvent(payload: unknown, env: unknown): PodMemberShiftEvent | null {
  const candidate = (env && typeof env === 'object' && 'pod_id' in env ? env : payload) as PodMemberShiftEvent | null;
  return candidate && typeof candidate === 'object' ? candidate : null;
}

const POD_COPY: Record<
  Language,
  {
    joined: string;
    left: string;
    closeDrawer: string;
    sendLabel: string;
    heroBadge: string;
    heroTitle: string;
    heroDesc: string;
    cityLabel: string;
    allCities: string;
    catAll: string;
    catWalk: string;
    catStudy: string;
    catGames: string;
    catLang: string;
    loadingPods: string;
    emptyTitle: string;
    quorumActive: string;
    forming: string;
    leaveBtn: string;
    chatBtn: string;
    waitingQuorum: string;
    joinBtn: string;
    noSeatsBtn: string;
    chatLockedErr: string;
    noMessagesYet: string;
    inputPlaceholder: string;
  }
> = {
  pl: {
    joined: 'Dołączono do poda!',
    left: 'Opuszczono poda.',
    closeDrawer: 'Zamknij czat poda',
    sendLabel: 'Wyślij wiadomość',
    heroBadge: 'NOWOŚĆ: BEZPIECZNE WYJŚCIA W MAŁYCH GRUPACH (3–5 OSÓB)',
    heroTitle: 'Odkryj Micro-Pody na Śląsku',
    heroDesc:
      'Zero presji i niezręczności spotkań 1-na-1 z nieznajomymi. Umawiaj się na krótkie wyjścia w zweryfikowanych miejscach publicznych (parki, biblioteki, kawiarnie). Czat grupy odblokowuje się automatycznie po osiągnięciu quorum (min. 3 osoby).',
    cityLabel: 'Miasto:',
    allCities: 'Wszystkie',
    catAll: 'Wszystkie aktywności',
    catWalk: 'Spacer w parku',
    catStudy: 'Sesja nauki',
    catGames: 'Gry planszowe',
    catLang: 'Wymiana językowa',
    loadingPods: 'Ładowanie dostępnych podów...',
    emptyTitle: 'Brak podów w wybranej kategorii',
    quorumActive: 'Quorum aktywne!',
    forming: 'Formowanie',
    leaveBtn: 'Opuść',
    chatBtn: 'Czat grupy',
    waitingQuorum: 'Oczekiwanie na quorum...',
    joinBtn: 'Dołącz do poda (+1 miejsce)',
    noSeatsBtn: 'Brak wolnych miejsc',
    chatLockedErr: 'Czat jest zablokowany do momentu osiągnięcia quorum (min. 3 osoby)',
    noMessagesYet: 'Brak wcześniejszych wiadomości. Przywitaj się z grupą!',
    inputPlaceholder: 'Napisz do grupy...',
  },
  en: {
    joined: 'Joined the pod!',
    left: 'Left the pod.',
    closeDrawer: 'Close pod chat',
    sendLabel: 'Send message',
    heroBadge: 'NEW: SAFE SMALL-GROUP OUTINGS (3–5 PEOPLE)',
    heroTitle: 'Discover Micro-Pods in Silesia',
    heroDesc:
      'No 1-on-1 pressure with strangers. Meet for structured activities at verified public third places (parks, libraries, cafés). Group chat unlocks automatically once quorum (min. 3 people) is reached.',
    cityLabel: 'City:',
    allCities: 'All',
    catAll: 'All activities',
    catWalk: 'Park walk',
    catStudy: 'Study session',
    catGames: 'Board games',
    catLang: 'Language exchange',
    loadingPods: 'Loading available pods...',
    emptyTitle: 'No pods in this category',
    quorumActive: 'Quorum active!',
    forming: 'Forming',
    leaveBtn: 'Leave',
    chatBtn: 'Group chat',
    waitingQuorum: 'Waiting for quorum...',
    joinBtn: 'Join pod (+1 seat)',
    noSeatsBtn: 'No seats left',
    chatLockedErr: 'Chat is locked until quorum (min. 3 people) is reached',
    noMessagesYet: 'No messages yet. Say hello to the group!',
    inputPlaceholder: 'Message the group...',
  },
  uk: {
    joined: 'Ви приєдналися до групи!',
    left: 'Ви залишили групу.',
    closeDrawer: 'Закрити чат групи',
    sendLabel: 'Надіслати повідомлення',
    heroBadge: 'НОВИНКА: БЕЗПЕЧНІ ЗУСТРІЧІ В МАЛИХ ГРУПАХ (3–5 ОСІБ)',
    heroTitle: 'Відкрийте Мікро-Групи в Сілезії',
    heroDesc:
      'Без напруги зустрічей сам на сам із незнайомцями. Домовляйтеся про короткі виходи у перевірених публічних місцях. Груповий чат відкривається автоматично після досягнення кворуму (мін. 3 особи).',
    cityLabel: 'Місто:',
    allCities: 'Усі',
    catAll: 'Усі активності',
    catWalk: 'Прогулянка в парку',
    catStudy: 'Спільне навчання',
    catGames: 'Настільні ігри',
    catLang: 'Мовний обмін',
    loadingPods: 'Завантаження доступних груп...',
    emptyTitle: 'Немає груп у вибраній категорії',
    quorumActive: 'Кворум активний!',
    forming: 'Формування',
    leaveBtn: 'Вийти',
    chatBtn: 'Чат групи',
    waitingQuorum: 'Очікування кворуму...',
    joinBtn: 'Приєднатися (+1 місце)',
    noSeatsBtn: 'Немає вільних місць',
    chatLockedErr: 'Чат заблоковано до досягнення кворуму (мін. 3 особи)',
    noMessagesYet: 'Повідомлень ще немає. Привітайтеся з групою!',
    inputPlaceholder: 'Напишіть групі...',
  },
  ru: {
    joined: 'Вы присоединились к группе!',
    left: 'Вы покинули группу.',
    closeDrawer: 'Закрыть чат группы',
    sendLabel: 'Отправить сообщение',
    heroBadge: 'НОВИНКА: БЕЗОПАСНЫЕ ВСТРЕЧИ В МАЛЫХ ГРУППАХ (3–5 ЧЕЛ.)',
    heroTitle: 'Откройте Микро-Группы в Силезии',
    heroDesc:
      'Без неловкости встреч 1-на-1 с незнакомцами. Встречайтесь в проверенных общественных местах (парки, библиотеки, кафе). Групповой чат открывается автоматически при достижении кворума (мин. 3 человека).',
    cityLabel: 'Город:',
    allCities: 'Все',
    catAll: 'Все активности',
    catWalk: 'Прогулка в парке',
    catStudy: 'Совместная учёба',
    catGames: 'Настольные игры',
    catLang: 'Языковой обмен',
    loadingPods: 'Загрузка доступных групп...',
    emptyTitle: 'Нет групп в выбранной категории',
    quorumActive: 'Кворум активен!',
    forming: 'Формирование',
    leaveBtn: 'Выйти',
    chatBtn: 'Чат группы',
    waitingQuorum: 'Ожидание кворума...',
    joinBtn: 'Присоединиться (+1 место)',
    noSeatsBtn: 'Нет свободных мест',
    chatLockedErr: 'Чат заблокирован до достижения кворума (мин. 3 человека)',
    noMessagesYet: 'Сообщений пока нет. Поприветствуйте группу!',
    inputPlaceholder: 'Напишите группе...',
  },
};

export const PodFeed: React.FC<PodFeedProps> = ({ token, currentUserId, onRequireAuth, lang = 'pl' }) => {
  const copy = POD_COPY[lang] || POD_COPY.pl;
  const [pods, setPods] = useState<Pod[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{ type: 'error' | 'success'; message: string } | null>(null);
  const [selectedCity, setSelectedCity] = useState<string>('Wszystkie');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Chat drawer state
  const [activePodChat, setActivePodChat] = useState<Pod | null>(null);
  const [chatMessages, setChatMessages] = useState<PodMessage[]>([]);
  const [messageText, setMessageText] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  useDialogFocus('pod-chat-drawer-dialog', Boolean(activePodChat), () => setActivePodChat(null));

  const loadFeed = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const cityFilter = selectedCity === 'Wszystkie' ? undefined : selectedCity;
      const data = await fetchPodFeed(cityFilter, token);
      setPods(data);
    } catch (err: any) {
      setError(err.message || 'Nie udało się pobrać listy podów');
    } finally {
      setLoading(false);
    }
  }, [selectedCity, token]);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    void loadFeed();
  }, [loadFeed]);

  // Feed-level realtime subscription: subscribe to joined pods and listen for quorum shifts even when drawer is closed
  const joinedPodIdsKey = pods
    .filter((p) => p.is_member || p.members.some((m) => m.user_id === currentUserId))
    .map((p) => p.id)
    .sort((a, b) => a - b)
    .join(',');

  useEffect(() => {
    if (!token) return;
    const channels = joinedPodIdsKey
      ? joinedPodIdsKey.split(',').map((id) => `pod:${id}`)
      : [];
    channels.forEach((ch) => realtime.subscribe(ch));

    const handleMemberShift = (payload: unknown, env: unknown) => {
      const data = unwrapPodShiftEvent(payload, env);
      if (!data || typeof data.pod_id !== 'number') return;

      setPods((prev) =>
        prev.map((p) => {
          if (p.id !== data.pod_id) return p;
          const nextCount = typeof data.confirmed_count === 'number' ? data.confirmed_count : p.confirmed_count;
          const nextStatus = data.status || p.status;
          return {
            ...p,
            confirmed_count: nextCount,
            spots_left: Math.max(0, p.max_participants - nextCount),
            status: nextStatus,
          };
        })
      );

      setActivePodChat((prev) => {
        if (!prev || prev.id !== data.pod_id) return prev;
        const nextCount = typeof data.confirmed_count === 'number' ? data.confirmed_count : prev.confirmed_count;
        const nextStatus = data.status || prev.status;
        if (nextStatus === 'forming') {
          setChatError(copy.chatLockedErr);
        } else if (nextStatus === 'quorum') {
          setChatError(null);
        }
        return {
          ...prev,
          confirmed_count: nextCount,
          spots_left: Math.max(0, prev.max_participants - nextCount),
          status: nextStatus,
        };
      });

      void loadFeed();
    };

    const unsubJoined = realtime.on('pod.member_joined', handleMemberShift);
    const unsubLeft = realtime.on('pod.member_left', handleMemberShift);

    return () => {
      unsubJoined();
      unsubLeft();
      channels.forEach((ch) => realtime.unsubscribe(ch));
    };
  }, [token, joinedPodIdsKey, loadFeed, copy.chatLockedErr]);

  // Realtime subscription to active pod chat messages when drawer is open
  useEffect(() => {
    if (!activePodChat || !token) return;
    const channel = `pod:${activePodChat.id}`;
    realtime.subscribe(channel);

    const unsubMsg = realtime.on('pod_chat_message', (payload: any, env: any) => {
      const msg = env?.message || payload?.message || payload;
      if (msg && msg.pod_id === activePodChat.id) {
        setChatMessages((prev) => {
          if (prev.some((m) => m.id === msg.id)) return prev;
          return [...prev, msg];
        });
      }
    });

    return () => {
      unsubMsg();
      if (!joinedPodIdsKey.split(',').includes(String(activePodChat.id))) {
        realtime.unsubscribe(channel);
      }
    };
  }, [activePodChat, token, joinedPodIdsKey]);

  const handleJoin = async (pod: Pod) => {
    if (!token) {
      onRequireAuth?.();
      return;
    }
    setActionFeedback(null);
    try {
      await joinPod(pod.id, token);
      setActionFeedback({ type: 'success', message: copy.joined });
      await loadFeed();
    } catch (err: any) {
      setActionFeedback({ type: 'error', message: err.message || 'Błąd dołączania do poda' });
    }
  };

  const handleLeave = async (pod: Pod) => {
    if (!token) return;
    setActionFeedback(null);
    try {
      await leavePod(pod.id, token);
      if (activePodChat?.id === pod.id) {
        setActivePodChat(null);
      }
      setActionFeedback({ type: 'success', message: copy.left });
      await loadFeed();
    } catch (err: any) {
      setActionFeedback({ type: 'error', message: err.message || 'Błąd opuszczania poda' });
    }
  };

  const openChat = async (pod: Pod) => {
    if (!token) {
      onRequireAuth?.();
      return;
    }
    setActivePodChat(pod);
    setChatError(null);
    try {
      const msgs = await fetchPodMessages(pod.id, token);
      setChatMessages(msgs);
    } catch (err: any) {
      setChatError(err.message || 'Czat jest zablokowany do momentu osiągnięcia quorum (min. 3 osoby)');
      setChatMessages([]);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !activePodChat || !messageText.trim()) return;
    try {
      setSendingMsg(true);
      setChatError(null);
      const newMsg = await sendPodMessage(activePodChat.id, messageText, token);
      setChatMessages((prev) => [...prev, newMsg]);
      setMessageText('');
    } catch (err: any) {
      setChatError(err.message || 'Nie udało się wysłać wiadomości');
    } finally {
      setSendingMsg(false);
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
    } catch {
      return isoString;
    }
  };

  // Get template visual theme (inspired by modern marketplace cards)
  const getTemplateTheme = (code: string) => {
    switch (code) {
      case 'park_walk':
        return {
          icon: '🌳',
          accent: 'emerald',
          badgeBg: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300',
          gradient: 'from-emerald-950/40 via-slate-900/90 to-slate-950',
          title: 'Spacer w parku',
        };
      case 'study_sprint':
        return {
          icon: '📚',
          accent: 'blue',
          badgeBg: 'bg-blue-500/15 border-blue-500/30 text-blue-300',
          gradient: 'from-blue-950/40 via-slate-900/90 to-slate-950',
          title: 'Nauka / Coworking',
        };
      case 'board_games':
        return {
          icon: '🎲',
          accent: 'amber',
          badgeBg: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
          gradient: 'from-amber-950/40 via-slate-900/90 to-slate-950',
          title: 'Gry planszowe',
        };
      case 'language_exchange':
        return {
          icon: '🗣️',
          accent: 'violet',
          badgeBg: 'bg-violet-500/15 border-violet-500/30 text-violet-300',
          gradient: 'from-violet-950/40 via-slate-900/90 to-slate-950',
          title: 'Wymiana językowa',
        };
      default:
        return {
          icon: '✨',
          accent: 'indigo',
          badgeBg: 'bg-indigo-500/15 border-indigo-500/30 text-indigo-300',
          gradient: 'from-indigo-950/40 via-slate-900/90 to-slate-950',
          title: 'Spotkanie w grupie',
        };
    }
  };

  // Filter pods by category
  const filteredPods = pods.filter((pod) => {
    if (selectedCategory === 'all') return true;
    return pod.template_code === selectedCategory;
  });

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-6 pb-28">
      {/* --- Elevated Marketplace / Timeleft Hero Banner --- */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-950/90 via-slate-900 to-slate-950 border border-indigo-500/30 p-6 sm:p-8 mb-8 shadow-2xl">
        {/* Ambient background glow orbs */}
        <div className="absolute -right-12 -top-12 w-56 h-56 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-12 -bottom-12 w-48 h-48 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>{copy.heroBadge}</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white mb-2.5">
            {copy.heroTitle}
          </h1>

          <p className="text-slate-300 text-xs sm:text-sm max-w-2xl leading-relaxed mb-6">
            {copy.heroDesc}
          </p>

          {/* Value props micro-pills */}
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-300 mb-6">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-800/80 border border-slate-700/80 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Sprawdzone Third Places
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-800/80 border border-slate-700/80 font-medium">
              <Users className="w-3.5 h-3.5 text-indigo-400" />
              Gwarancja Quorum (3-5 osób)
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-800/80 border border-slate-700/80 font-medium">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Zero oczekiwanych wydatków
            </span>
          </div>

          {/* City Filter Pills */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80">
            <span className="text-xs font-bold text-slate-400 mr-1 flex items-center gap-1">
              <Compass className="w-3.5 h-3.5" /> {copy.cityLabel}
            </span>
            {['Wszystkie', 'Katowice', 'Chorzów', 'Gliwice'].map((city) => (
              <button
                key={city}
                onClick={() => setSelectedCity(city)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                  selectedCity === city
                    ? 'bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/25 border border-indigo-400/30'
                    : 'bg-slate-900/80 text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700'
                }`}
              >
                {city === 'Wszystkie' ? copy.allCities : city}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* --- Activity Category Filter Chips --- */}
      <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-6 no-scrollbar">
        {[
          { id: 'all', label: copy.catAll, icon: '✨' },
          { id: 'park_walk', label: copy.catWalk, icon: '🌳' },
          { id: 'study_sprint', label: copy.catStudy, icon: '📚' },
          { id: 'board_games', label: copy.catGames, icon: '🎲' },
          { id: 'language_exchange', label: copy.catLang, icon: '🗣️' },
        ].map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition cursor-pointer flex items-center gap-1.5 ${
              selectedCategory === cat.id
                ? 'bg-slate-800 text-white border border-slate-600 shadow-sm'
                : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/60'
            }`}
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
          </button>
        ))}
      </div>

      {/* Action Feedback Banner */}
      {actionFeedback && (
        <div
          role="status"
          className={`p-3.5 rounded-2xl border flex items-center justify-between gap-3 mb-4 text-xs transition-all ${
            actionFeedback.type === 'error'
              ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
              : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionFeedback.type === 'error' ? (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            )}
            <span className="font-medium">{actionFeedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionFeedback(null)}
            aria-label="Zamknij powiadomienie"
            className="text-slate-400 hover:text-white min-h-[32px] min-w-[32px] flex items-center justify-center cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Loading & Error States */}
      {loading && (
        <div className="flex flex-col justify-center items-center py-16 gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent"></div>
          <span className="text-xs text-slate-400 font-medium">{copy.loadingPods}</span>
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 text-rose-300 p-4 rounded-2xl border border-rose-500/30 flex items-center gap-3 mb-6 text-xs">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredPods.length === 0 && (
        <div className="glass-card rounded-3xl p-12 text-center border border-dashed border-slate-800">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-indigo-400" />
          </div>
          <h3 className="text-base font-bold text-white mb-1.5">{copy.emptyTitle}</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Wkrótce pojawią się nowe zaplanowane wyjścia w sprawdzonych lokalizacjach w Twojej okolicy.
          </p>
        </div>
      )}

      {/* --- Pods Marketplace Grid --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filteredPods.map((pod) => {
          const isAtQuorum = pod.status === 'quorum' || pod.status === 'completed';
          const isJoined = pod.is_member || pod.members.some((m) => m.user_id === currentUserId);
          const theme = getTemplateTheme(pod.template_code);
          const spotsNeeded = Math.max(0, pod.min_participants - pod.confirmed_count);

          return (
            <div
              key={pod.id}
              className={`glass-card rounded-2xl p-5 border border-slate-800/80 hover:border-indigo-500/40 transition flex flex-col justify-between shadow-xl relative overflow-hidden bg-gradient-to-b ${theme.gradient}`}
            >
              <div>
                {/* Header: Template badge & Quorum pill */}
                <div className="flex items-start justify-between gap-2 mb-3.5">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border ${theme.badgeBg}`}>
                    <span>{theme.icon}</span>
                    <span>{pod.template_name || theme.title} · {pod.template_duration_min} min</span>
                  </span>

                  {isAtQuorum ? (
                    <span className="inline-flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shrink-0">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      {copy.quorumActive}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 shrink-0">
                      <Clock className="w-3 h-3 text-amber-400" />
                      {copy.forming}
                    </span>
                  )}
                </div>

                {/* Title */}
                <h2 className="text-base font-bold text-white leading-snug mb-3">
                  {pod.title || pod.template_name}
                </h2>

                {/* Third Place Venue & Logistics Card */}
                <div className="space-y-2 text-xs bg-slate-950/60 border border-slate-800/80 p-3.5 rounded-xl mb-4">
                  <div className="flex items-center gap-2 font-semibold text-slate-100">
                    <MapPin className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    <span>{pod.place_name} ({pod.place_city})</span>
                  </div>
                  <div className="pl-5 text-slate-400">
                    Zbiórka: <span className="text-slate-200 font-medium">{pod.place_meeting_point}</span>
                  </div>
                  <div className="pl-5 text-slate-400 flex items-center gap-1.5">
                    <Calendar className="w-3 h-3 text-indigo-400" />
                    <span>{formatDate(pod.starts_at)}, {formatTime(pod.starts_at)} – {formatTime(pod.ends_at)}</span>
                  </div>
                  <div className="pl-5 text-slate-400">
                    Wydatki: <span className="text-emerald-400 font-medium">
                      {pod.spend_expectation === 'no_expected_spend' ? 'Bezpłatnie (0 zł)' : 'Płatność za siebie'}
                    </span>
                  </div>
                </div>

                {/* Segmented Seat Progress Bar */}
                <div className="mb-4">
                  <div className="flex justify-between items-center text-xs font-semibold mb-2">
                    <span className="flex items-center gap-1.5 text-slate-300">
                      <Users className="w-3.5 h-3.5 text-indigo-400" />
                      Zajęte miejsca: {pod.confirmed_count} / {pod.max_participants}
                    </span>
                    <span className="text-slate-400 text-[11px]">
                      {pod.spots_left > 0 ? `Wolne: ${pod.spots_left}` : 'Pełny pod'}
                    </span>
                  </div>

                  {/* 5 Segmented Capacity Blocks */}
                  <div className="grid grid-cols-5 gap-1.5 h-2.5">
                    {Array.from({ length: pod.max_participants }).map((_, i) => {
                      const isOccupied = i < pod.confirmed_count;
                      const isQuorumThreshold = i < pod.min_participants;
                      return (
                        <div
                          key={i}
                          className={`rounded-full transition-all duration-300 ${
                            isOccupied
                              ? isAtQuorum
                                ? 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-sm shadow-emerald-500/20'
                                : 'bg-gradient-to-r from-indigo-500 to-violet-500'
                              : isQuorumThreshold
                              ? 'bg-slate-800 border border-slate-700/80'
                              : 'bg-slate-850 border border-slate-800'
                          }`}
                          title={`Miejsce ${i + 1}${isOccupied ? ' (Zajęte)' : ' (Wolne)'}`}
                        />
                      );
                    })}
                  </div>

                  {!isAtQuorum && (
                    <div className="text-[11px] text-amber-300 font-medium mt-2 flex items-center gap-1">
                      <span>⚡</span>
                      <span>Potrzeba jeszcze {spotsNeeded} {spotsNeeded === 1 ? 'osoby' : 'osób'} do odblokowania czatu</span>
                    </div>
                  )}
                </div>

                {/* Facepile / Attendee Avatars */}
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-[11px] text-slate-400 font-medium">Uczestnicy:</span>
                  <div className="flex -space-x-2 overflow-hidden items-center">
                    {pod.members.map((m, idx) => (
                      <div
                        key={m.user_id || idx}
                        title={m.name}
                        className="inline-block h-7 w-7 rounded-full ring-2 ring-slate-900 bg-gradient-to-tr from-indigo-600 to-violet-500 text-white text-[11px] font-bold flex items-center justify-center uppercase shadow"
                      >
                        {m.name ? m.name.charAt(0) : 'U'}
                      </div>
                    ))}
                    {Array.from({ length: Math.min(3, pod.spots_left) }).map((_, idx) => (
                      <div
                        key={idx}
                        className="inline-block h-7 w-7 rounded-full ring-2 ring-slate-900 border border-dashed border-slate-600 bg-slate-900/60 text-slate-500 text-[10px] font-bold flex items-center justify-center"
                        title="Wolne miejsce"
                      >
                        +1
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center gap-2.5">
                {isJoined ? (
                  <>
                    <button
                      onClick={() => handleLeave(pod)}
                      className="py-2.5 px-3.5 border border-slate-700 hover:bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold transition cursor-pointer"
                    >
                      {copy.leaveBtn}
                    </button>
                    {isAtQuorum ? (
                      <button
                        onClick={() => openChat(pod)}
                        className="flex-1 py-2.5 px-4 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 transition shadow-lg shadow-emerald-500/20 cursor-pointer"
                      >
                        <MessageSquare className="w-4 h-4" />
                        <span>{copy.chatBtn}</span>
                        <ChevronRight className="w-3.5 h-3.5 opacity-70" />
                      </button>
                    ) : (
                      <div className="flex-1 py-2 px-3 text-center text-xs text-amber-300/80 bg-amber-500/10 border border-amber-500/20 rounded-xl font-medium">
                        {copy.waitingQuorum}
                      </div>
                    )}
                  </>
                ) : (
                  <button
                    disabled={pod.spots_left <= 0}
                    onClick={() => handleJoin(pod)}
                    className="w-full py-3 px-4 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 cursor-pointer"
                  >
                    <Users className="w-4 h-4" />
                    <span>{pod.spots_left > 0 ? copy.joinBtn : copy.noSeatsBtn}</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* --- Slide-in Group Chat Drawer Modal (Dark Glassmorphic) --- */}
      {activePodChat && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex justify-end">
          <div
            id="pod-chat-drawer-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="pod-chat-drawer-title"
            tabIndex={-1}
            className="w-full max-w-md bg-slate-950/95 border-l border-slate-800 h-full shadow-2xl flex flex-col justify-between"
          >
            {/* Chat Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60 backdrop-blur-md">
              <div>
                <div className="text-[11px] font-bold text-emerald-400 flex items-center gap-1 mb-0.5">
                  <CheckCircle2 className="w-3 h-3" /> Quorum aktywne ({activePodChat.confirmed_count} osób)
                </div>
                <h3 id="pod-chat-drawer-title" className="text-sm font-bold text-white truncate max-w-[260px]">
                  {activePodChat.title || activePodChat.template_name}
                </h3>
                <p className="text-[11px] text-slate-400">
                  {activePodChat.place_name} · {activePodChat.place_meeting_point}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActivePodChat(null)}
                aria-label={copy.closeDrawer}
                className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {chatError && (
                <div className="p-3 bg-amber-500/10 text-amber-300 rounded-xl text-xs border border-amber-500/30 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>{chatError}</span>
                </div>
              )}

              {chatMessages.length === 0 && !chatError && (
                <div className="text-center py-12 text-xs text-slate-500 flex flex-col items-center gap-2">
                  <MessageSquare className="w-8 h-8 text-slate-600" />
                  <span>Brak wcześniejszych wiadomości. Przywitaj się z grupą!</span>
                </div>
              )}

              {chatMessages.map((msg) => {
                const isMe = msg.sender_user_id === currentUserId;
                return (
                  <div key={msg.id} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                    <span className="text-[10px] text-slate-400 mb-1 px-1 font-medium">
                      {isMe ? 'Ty' : msg.sender_name} · {formatTime(msg.created_at)}
                    </span>
                    <div
                      className={`max-w-[82%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-sm ${
                        isMe
                          ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-br-sm'
                          : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-sm'
                      }`}
                    >
                      {msg.body}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-800 bg-slate-900/60 backdrop-blur-md flex gap-2">
              <input
                type="text"
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                placeholder="Napisz do grupy..."
                aria-label="Treść wiadomości"
                className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                disabled={sendingMsg || !messageText.trim()}
                aria-label={copy.sendLabel}
                className="p-3 bg-gradient-to-tr from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 disabled:opacity-40 text-white rounded-xl transition flex items-center justify-center cursor-pointer shadow-md shadow-indigo-500/20"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PodFeed;
