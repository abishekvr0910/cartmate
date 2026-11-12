import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  PhoneCall,
  PhoneOff,
  Mic,
  MicOff,
  Volume2,
  ShieldAlert,
  Clock,
  Sparkles,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import type { User, VoiceStatusResponse, VoiceCallPeer } from '../types';
import type { Language } from '../locales';
import { fetchVoiceStatus, rateVoiceCall, hangupVoiceCall, trackEvent } from '../api';
import { realtime } from '../realtime/socket';
import { useDialogFocus } from '../hooks/useDialogFocus';

interface VoiceCallHUDProps {
  token: string | null;
  currentUser: User | null;
  lang?: Language;
}

type CallState = 'idle' | 'searching' | 'connecting' | 'in_call' | 'ended';

const VOICE_MILESTONES: Record<Language, { m5: string; m1: string; s30: string }> = {
  pl: { m5: 'Pozostało 5 minut rozmowy.', m1: 'Pozostała 1 minuta rozmowy.', s30: 'Pozostało 30 sekund rozmowy.' },
  en: { m5: '5 minutes remaining in call.', m1: '1 minute remaining in call.', s30: '30 seconds remaining in call.' },
  uk: { m5: 'Залишилося 5 хвилин розмови.', m1: 'Залишилася 1 хвилина розмови.', s30: 'Залишилося 30 секунд розмови.' },
  ru: { m5: 'Осталось 5 минут разговора.', m1: 'Осталась 1 минута разговора.', s30: 'Осталось 30 секунд разговора.' },
};

const VOICE_COPY: Record<
  Language,
  {
    title: string;
    subtitle: string;
    searchingTitle: string;
    cancelSearch: string;
    windowStatus: string;
    windowOpen: string;
    windowClosed: string;
    connectNow: string;
    rateTitle: string;
    rateThanks: string;
    refresh: string;
    encryptedNotice: string;
    connectingPeer: string;
    topicLabel: string;
    limit10: string;
    icebreakerPrompt: string;
    anotherQuestion: string;
    unmuteMic: string;
    muteMic: string;
    micOnLabel: string;
    micOffLabel: string;
    endCallTitle: string;
    endLabel: string;
    endBlockTitle: string;
    blockLabel: string;
    blockConfirmTitle: string;
    blockConfirmBody: string;
    cancel: string;
    blockNow: string;
    searchingBody: string;
    callsUsedToday: string;
    cooldownLabel: string;
    cooldownNone: string;
    safeSpaceTitle: string;
    safeRule1: string;
    safeRule2: string;
    safeRule3: string;
    safeRule4: string;
    chooseTopic: string;
    defaultTopic1: string;
    defaultTopic2: string;
    defaultTopic3: string;
    windowClosedButton: string;
    dailyLimitReached: string;
    ratingHelps: string;
    ratingAnonymous: string;
    ratingRespectful: string;
    ratingNeutral: string;
    ratingInappropriate: string;
    ratingPlaceholder: string;
    ratingBlock: string;
    ratingSkip: string;
    ratingSave: string;
    errorStatus: string;
    errorRating: string;
    noCallers: string;
    micError: (detail: string) => string;
    cooldownButton: (seconds: number) => string;
    speakerOnLabel: string;
    speakerOffLabel: string;
    micSilentWarning: string;
  }
> = {
  pl: {
    title: '10-Minutowe Rozmowy',
    subtitle: 'Anonimowe, bezpieczne połączenia audio',
    searchingTitle: 'Szukamy rozmówcy...',
    cancelSearch: 'Anuluj wyszukiwanie',
    windowStatus: 'Status okna rozmów',
    windowOpen: 'Otwarte (18:00 - 23:00)',
    windowClosed: 'Zamknięte (18:00 - 23:00)',
    connectNow: 'Połącz z kimś teraz (10 min)',
    rateTitle: 'Jak przebiegła rozmowa?',
    rateThanks: 'Dziękujemy za ocenę!',
    refresh: 'Odśwież',
    encryptedNotice: 'Szyfrowane audio • Bez nagrywania',
    connectingPeer: 'Łączenie rozmówcy...',
    topicLabel: 'Temat:',
    limit10: 'Limit 10:00',
    icebreakerPrompt: 'Pomysł na temat / pytanie:',
    anotherQuestion: 'Inne pytanie',
    unmuteMic: 'Wyłącz wyciszenie',
    muteMic: 'Wycisz mikrofon',
    micOnLabel: 'Mikrofon',
    micOffLabel: 'Wycisz',
    endCallTitle: 'Zakończ rozmowę',
    endLabel: 'Koniec',
    endBlockTitle: 'Zakończ i Zablokuj',
    blockLabel: 'Zablokuj',
    blockConfirmTitle: 'Zakończyć i zablokować?',
    blockConfirmBody:
      'Rozmowa zostanie natychmiast przerwana, a ten rozmówca nie będzie mógł połączyć się z Tobą ani pisać w żadnym kanale.',
    cancel: 'Anuluj',
    blockNow: 'Zablokuj teraz',
    searchingBody: 'Dopasowujemy osobę z Twojego regionu na spokojną 10-minutową rozmowę.',
    callsUsedToday: 'Dziś wykorzystano',
    cooldownLabel: 'Przerwa po rozmowie',
    cooldownNone: 'Brak (gotowy)',
    safeSpaceTitle: 'Gwarancja bezpiecznej i życzliwej przestrzeni',
    safeRule1: 'Rozmowa trwa dokładnie 10 minut i kończy się automatycznie.',
    safeRule2: 'Widoczne jest tylko Twoje imię i miasto (zero numerów telefonów).',
    safeRule3: 'W każdej chwili masz 1-tap przycisk zakończenia i blokady.',
    safeRule4: 'Połączenie jest bezpośrednie (P2P audio) bez zapisu na serwerze.',
    chooseTopic: 'Wybierz temat przewodni rozmowy:',
    defaultTopic1: 'Jak minął Ci dzisiejszy dzień?',
    defaultTopic2: 'Twój ulubiony sprawdzony przepis na obiad?',
    defaultTopic3: 'Ciekawy film, serial lub książka warta polecenia?',
    windowClosedButton: 'Okno rozmów zamknięte (18:00 - 23:00)',
    dailyLimitReached: 'Osiągnięto limit dzienny (3/3)',
    ratingHelps: 'Pomagasz utrzymać życzliwą społeczność.',
    ratingAnonymous: 'Twoja opinia jest w 100% anonimowa.',
    ratingRespectful: 'Miła',
    ratingNeutral: 'Neutralna',
    ratingInappropriate: 'Nie na temat',
    ratingPlaceholder: 'Dodatkowe uwagi (opcjonalnie)...',
    ratingBlock: 'Zablokuj tego rozmówcę na przyszłość',
    ratingSkip: 'Pomiń',
    ratingSave: 'Zapisz ocenę',
    errorStatus: 'Nie udało się pobrać statusu połączeń.',
    errorRating: 'Nie udało się zapisać oceny: ',
    noCallers: 'Brak dostępnych rozmówców w tej chwili.',
    micError: (detail) => `Błąd dostępu do mikrofonu: ${detail}`,
    cooldownButton: (seconds) => `Przerwa: ${seconds}s`,
    speakerOnLabel: 'Głośnik',
    speakerOffLabel: 'Słuchawka',
    micSilentWarning: 'Mikrofon nie rejestruje dźwięku. Sprawdź, czy nie jest wyciszony sprzętowo.',
  },
  en: {
    title: '10-Minute Voice',
    subtitle: 'Ephemeral anonymous audio calls',
    searchingTitle: 'Searching for a caller...',
    cancelSearch: 'Cancel search',
    windowStatus: 'Call window status',
    windowOpen: 'Open (18:00 - 23:00)',
    windowClosed: 'Closed (18:00 - 23:00)',
    connectNow: 'Connect now (10 min)',
    rateTitle: 'How was the call?',
    rateThanks: 'Thank you for rating!',
    refresh: 'Refresh',
    encryptedNotice: 'Encrypted audio • No recording',
    connectingPeer: 'Connecting caller...',
    topicLabel: 'Topic:',
    limit10: 'Limit 10:00',
    icebreakerPrompt: 'Topic / question idea:',
    anotherQuestion: 'Another question',
    unmuteMic: 'Unmute microphone',
    muteMic: 'Mute microphone',
    micOnLabel: 'Mic',
    micOffLabel: 'Muted',
    endCallTitle: 'End call',
    endLabel: 'End',
    endBlockTitle: 'End and block',
    blockLabel: 'Block',
    blockConfirmTitle: 'End and block?',
    blockConfirmBody:
      'The call will end immediately and this caller will not be able to connect with you or message you on any channel.',
    cancel: 'Cancel',
    blockNow: 'Block now',
    searchingBody: 'We are matching you with someone from your region for a calm 10-minute call.',
    callsUsedToday: 'Used today',
    cooldownLabel: 'Post-call cooldown',
    cooldownNone: 'None (ready)',
    safeSpaceTitle: 'Guaranteed safe and kind space',
    safeRule1: 'The call lasts exactly 10 minutes and ends automatically.',
    safeRule2: 'Only your first name and city are visible (no phone numbers).',
    safeRule3: 'You have a one-tap end and block button at all times.',
    safeRule4: 'The connection is direct (P2P audio) with no server recording.',
    chooseTopic: 'Choose the main conversation topic:',
    defaultTopic1: 'How was your day today?',
    defaultTopic2: 'Your favorite tried-and-true dinner recipe?',
    defaultTopic3: 'An interesting film, series, or book worth recommending?',
    windowClosedButton: 'Call window closed (18:00 - 23:00)',
    dailyLimitReached: 'Daily limit reached (3/3)',
    ratingHelps: 'You help keep the community kind.',
    ratingAnonymous: 'Your feedback is 100% anonymous.',
    ratingRespectful: 'Kind',
    ratingNeutral: 'Neutral',
    ratingInappropriate: 'Off-topic',
    ratingPlaceholder: 'Additional notes (optional)...',
    ratingBlock: 'Block this caller in the future',
    ratingSkip: 'Skip',
    ratingSave: 'Save rating',
    errorStatus: 'Failed to load call status.',
    errorRating: 'Failed to save rating: ',
    noCallers: 'No callers available right now.',
    micError: (detail) => `Microphone access error: ${detail}`,
    cooldownButton: (seconds) => `Cooldown: ${seconds}s`,
    speakerOnLabel: 'Speaker',
    speakerOffLabel: 'Earpiece',
    micSilentWarning: 'Microphone is not capturing sound. Check your physical mute switch.',
  },
  uk: {
    title: '10-Хвилинні Розмови',
    subtitle: 'Анонімні безпечні аудіодзвінки',
    searchingTitle: 'Шукаємо співрозмовника...',
    cancelSearch: 'Скасувати пошук',
    windowStatus: 'Статус вікна розмов',
    windowOpen: 'Відкрито (18:00 - 23:00)',
    windowClosed: 'Закрито (18:00 - 23:00)',
    connectNow: 'З’єднатися зараз (10 хв)',
    rateTitle: 'Як пройшла розмова?',
    rateThanks: 'Дякуємо за оцінку!',
    refresh: 'Оновити',
    encryptedNotice: 'Зашифроване аудіо • Без запису',
    connectingPeer: 'З’єднання зі співрозмовником...',
    topicLabel: 'Тема:',
    limit10: 'Ліміт 10:00',
    icebreakerPrompt: 'Ідея теми / питання:',
    anotherQuestion: 'Інше питання',
    unmuteMic: 'Увімкнути мікрофон',
    muteMic: 'Вимкнути мікрофон',
    micOnLabel: 'Мікрофон',
    micOffLabel: 'Без звуку',
    endCallTitle: 'Завершити розмову',
    endLabel: 'Кінець',
    endBlockTitle: 'Завершити й заблокувати',
    blockLabel: 'Заблокувати',
    blockConfirmTitle: 'Завершити й заблокувати?',
    blockConfirmBody:
      'Розмова буде негайно перервана, і цей співрозмовник не зможе зв’язатися з вами або писати в жодному каналі.',
    cancel: 'Скасувати',
    blockNow: 'Заблокувати зараз',
    searchingBody: 'Ми підбираємо людину з вашого регіону для спокійної 10-хвилинної розмови.',
    callsUsedToday: 'Використано сьогодні',
    cooldownLabel: 'Перерва після розмови',
    cooldownNone: 'Немає (готово)',
    safeSpaceTitle: 'Гарантія безпечного й доброзичливого простору',
    safeRule1: 'Розмова триває рівно 10 хвилин і завершується автоматично.',
    safeRule2: 'Видно лише ваше ім’я та місто (без номерів телефонів).',
    safeRule3: 'У будь-який момент доступна кнопка завершення й блокування одним дотиком.',
    safeRule4: 'З’єднання пряме (P2P аудіо) без запису на сервері.',
    chooseTopic: 'Оберіть головну тему розмови:',
    defaultTopic1: 'Як минув ваш день?',
    defaultTopic2: 'Ваш улюблений перевірений рецепт вечері?',
    defaultTopic3: 'Цікавий фільм, серіал або книга, варті рекомендації?',
    windowClosedButton: 'Вікно розмов зачинено (18:00 - 23:00)',
    dailyLimitReached: 'Досягнуто денного ліміту (3/3)',
    ratingHelps: 'Ви допомагаєте підтримувати доброзичливу спільноту.',
    ratingAnonymous: 'Ваш відгук на 100% анонімний.',
    ratingRespectful: 'Приємна',
    ratingNeutral: 'Нейтральна',
    ratingInappropriate: 'Не за темою',
    ratingPlaceholder: 'Додаткові зауваження (необов’язково)...',
    ratingBlock: 'Заблокувати цього співрозмовника на майбутнє',
    ratingSkip: 'Пропустити',
    ratingSave: 'Зберегти оцінку',
    errorStatus: 'Не вдалося завантажити статус дзвінків.',
    errorRating: 'Не вдалося зберегти оцінку: ',
    noCallers: 'Зараз немає доступних співрозмовників.',
    micError: (detail) => `Помилка доступу до мікрофона: ${detail}`,
    cooldownButton: (seconds) => `Перерва: ${seconds}s`,
    speakerOnLabel: 'Динамік',
    speakerOffLabel: 'Навушник',
    micSilentWarning: 'Мікрофон не вловлює звук. Перевірте апаратне вимкнення звуку.',
  },
  ru: {
    title: '10-Минутные Разговоры',
    subtitle: 'Анонимные безопасные аудиозвонки',
    searchingTitle: 'Ищем собеседника...',
    cancelSearch: 'Отменить поиск',
    windowStatus: 'Статус окна звонков',
    windowOpen: 'Открыто (18:00 - 23:00)',
    windowClosed: 'Закрыто (18:00 - 23:00)',
    connectNow: 'Соединиться сейчас (10 мин)',
    rateTitle: 'Как прошёл разговор?',
    rateThanks: 'Спасибо за оценку!',
    refresh: 'Обновить',
    encryptedNotice: 'Зашифрованное аудио • Без записи',
    connectingPeer: 'Соединение с собеседником...',
    topicLabel: 'Тема:',
    limit10: 'Лимит 10:00',
    icebreakerPrompt: 'Идея темы / вопроса:',
    anotherQuestion: 'Другой вопрос',
    unmuteMic: 'Включить микрофон',
    muteMic: 'Выключить микрофон',
    micOnLabel: 'Микрофон',
    micOffLabel: 'Без звука',
    endCallTitle: 'Завершить звонок',
    endLabel: 'Конец',
    endBlockTitle: 'Завершить и заблокировать',
    blockLabel: 'Заблокировать',
    blockConfirmTitle: 'Завершить и заблокировать?',
    blockConfirmBody:
      'Звонок будет немедленно прерван, и этот собеседник не сможет связаться с вами или писать ни в одном канале.',
    cancel: 'Отмена',
    blockNow: 'Заблокировать сейчас',
    searchingBody: 'Мы подбираем человека из вашего региона для спокойного 10-минутного разговора.',
    callsUsedToday: 'Использовано сегодня',
    cooldownLabel: 'Пауза после звонка',
    cooldownNone: 'Нет (готово)',
    safeSpaceTitle: 'Гарантия безопасного и доброжелательного пространства',
    safeRule1: 'Звонок длится ровно 10 минут и завершается автоматически.',
    safeRule2: 'Видны только ваше имя и город (без номеров телефонов).',
    safeRule3: 'В любой момент доступна кнопка завершения и блокировки одним нажатием.',
    safeRule4: 'Соединение прямое (P2P аудио) без записи на сервере.',
    chooseTopic: 'Выберите главную тему разговора:',
    defaultTopic1: 'Как прошёл ваш день?',
    defaultTopic2: 'Ваш любимый проверенный рецепт ужина?',
    defaultTopic3: 'Интересный фильм, сериал или книга, достойные рекомендации?',
    windowClosedButton: 'Окно звонков закрыто (18:00 - 23:00)',
    dailyLimitReached: 'Достигнут дневной лимит (3/3)',
    ratingHelps: 'Вы помогаете поддерживать доброжелательное сообщество.',
    ratingAnonymous: 'Ваш отзыв на 100% анонимный.',
    ratingRespectful: 'Приятный',
    ratingNeutral: 'Нейтральный',
    ratingInappropriate: 'Не по теме',
    ratingPlaceholder: 'Дополнительные замечания (необязательно)...',
    ratingBlock: 'Заблокировать этого собеседника на будущее',
    ratingSkip: 'Пропустить',
    ratingSave: 'Сохранить оценку',
    errorStatus: 'Не удалось загрузить статус звонков.',
    errorRating: 'Не удалось сохранить оценку: ',
    noCallers: 'Сейчас нет доступных собеседников.',
    micError: (detail) => `Ошибка доступа к микрофону: ${detail}`,
    cooldownButton: (seconds) => `Пауза: ${seconds}s`,
    speakerOnLabel: 'Динамик',
    speakerOffLabel: 'Наушник',
    micSilentWarning: 'Микрофон не улавливает звук. Проверьте аппаратное выключение звука.',
  },
};

export const VoiceCallHUD: React.FC<VoiceCallHUDProps> = ({ token, currentUser: _currentUser, lang = 'pl' }) => {
  const milestones = VOICE_MILESTONES[lang] || VOICE_MILESTONES.pl;
  const vcopy = VOICE_COPY[lang] || VOICE_COPY.pl;
  const [statusData, setStatusData] = useState<VoiceStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [callState, setCallState] = useState<CallState>('idle');
  const [selectedTopic, setSelectedTopic] = useState<string>(vcopy.defaultTopic1);
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [peerInfo, setPeerInfo] = useState<VoiceCallPeer | null>(null);
  const [_callRole, setCallRole] = useState<'offerer' | 'answerer' | null>(null);

  // Audio & WebRTC State
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(600);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [waveLevels, setWaveLevels] = useState<number[]>(() => Array(9).fill(0));
  const [isMicSilent, setIsMicSilent] = useState<boolean>(false);
  const [isSpeakerphone, setIsSpeakerphone] = useState<boolean>(true);
  const [showBlockConfirm, setShowBlockConfirm] = useState<boolean>(false);

  // Rating State
  const [showRating, setShowRating] = useState<boolean>(false);
  const [lastCallId, setLastCallId] = useState<string | null>(null);
  const [selectedRating, setSelectedRating] = useState<'respectful' | 'neutral' | 'inappropriate'>('respectful');
  const [ratingDetails, setRatingDetails] = useState<string>('');
  const [ratingBlockPeer, setRatingBlockPeer] = useState<boolean>(false);
  const [ratingSubmitted, setRatingSubmitted] = useState<boolean>(false);

  useDialogFocus('voice-block-confirm-dialog', showBlockConfirm, () => setShowBlockConfirm(false));
  useDialogFocus('voice-rating-dialog', showRating, () => setShowRating(false));

  // Refs
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);
  const pendingCandidatesRef = useRef<RTCIceCandidateInit[]>([]);
  const pendingOfferRef = useRef<{ sdp: string; call_id?: string } | null>(null);
  const activeCallIdRef = useRef<string | null>(null);
  const callStateRef = useRef<CallState>('idle');
  const callSessionRef = useRef<number>(0);

  useEffect(() => {
    activeCallIdRef.current = activeCallId;
  }, [activeCallId]);

  useEffect(() => {
    callStateRef.current = callState;
  }, [callState]);

  const milestoneAnnouncement =
    callState === 'in_call'
      ? secondsRemaining === 300
        ? milestones.m5
        : secondsRemaining === 60
        ? milestones.m1
        : secondsRemaining === 30
        ? milestones.s30
        : ''
      : '';

  // Load Status
  const loadStatus = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await fetchVoiceStatus(token);
      setStatusData(data);
      if (data.icebreakers && data.icebreakers.length > 0) {
        setSelectedTopic((prev) => prev || data.icebreakers[0]);
      }
    } catch (err: any) {
      setErrorMsg(err.message || vcopy.errorStatus);
    } finally {
      setLoading(false);
    }
  }, [token, vcopy.errorStatus]);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    loadStatus();
    void trackEvent('voice_lobby_viewed', { lang });
  }, [loadStatus, lang]);

  // Cleanup WebRTC & Audio
  const cleanupMedia = useCallback(() => {
    callSessionRef.current += 1;
    pendingCandidatesRef.current = [];
    pendingOfferRef.current = null;
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    }
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setAudioLevel(0);
    setWaveLevels(Array(9).fill(0));
    setIsMicSilent(false);
  }, []);

  // Audio output device toggle (Speakerphone / Earpiece)
  const toggleSpeakerphone = useCallback(async () => {
    const audioEl = remoteAudioRef.current;
    try {
      if (audioEl && 'setSinkId' in HTMLMediaElement.prototype) {
        const devices = await navigator.mediaDevices?.enumerateDevices?.();
        const outputs = devices?.filter((d) => d.kind === 'audiooutput') || [];
        if (outputs.length > 1) {
          const target = isSpeakerphone ? outputs[1] : outputs[0];
          await (audioEl as any).setSinkId(target.deviceId);
        }
      }
      setIsSpeakerphone((prev) => !prev);
    } catch (err) {
      console.warn('Speakerphone toggle warning:', err);
      setIsSpeakerphone((prev) => !prev);
    }
  }, [isSpeakerphone]);

  const flushPendingCandidates = async (pc: RTCPeerConnection) => {
    if (!pc.remoteDescription) return;
    const queued = [...pendingCandidatesRef.current];
    pendingCandidatesRef.current = [];
    for (const cand of queued) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(cand));
      } catch (e) {
        console.warn('Error applying queued ICE candidate:', e);
      }
    }
  };

  useEffect(() => {
    return () => {
      cleanupMedia();
    };
  }, [cleanupMedia]);

  // Audio level analyser loop with Handy's logarithmic speech frequency bucketing & silence detection
  const startAudioAnalyser = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.3;
      source.connect(analyser);
      analyserRef.current = analyser;

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      const smoothedRef = Array(9).fill(0);
      let silentFrames = 0;

      const checkVolume = () => {
        analyser.getByteFrequencyData(dataArray);

        // Handy 9-bar logarithmic speech visualizer across speech frequencies (bins 1..48)
        const bucketRanges: [number, number][] = [
          [1, 2], [2, 4], [4, 7], [7, 11], [11, 16],
          [16, 22], [22, 29], [29, 37], [37, 48]
        ];

        let totalPower = 0;
        const rawBuckets: number[] = [];

        for (let b = 0; b < bucketRanges.length; b++) {
          const [start, end] = bucketRanges[b];
          let pSum = 0;
          for (let i = start; i < end; i++) {
            const mag = dataArray[i] || 0;
            pSum += mag * mag;
          }
          const avgP = pSum / (end - start);
          totalPower += avgP;

          // Convert to dB with Handy calibrated range: -68 dB to -25 dB
          const db = avgP > 1e-4 ? 20 * Math.log10(Math.sqrt(avgP) / 255) : -80;
          const DB_MIN = -68.0;
          const DB_MAX = -25.0;
          const normalized = Math.max(0, Math.min(1, (db - DB_MIN) / (DB_MAX - DB_MIN)));
          rawBuckets.push(normalized);
        }

        // Handy temporal exponential smoothing: prev * 0.7 + target * 0.3
        for (let b = 0; b < 9; b++) {
          smoothedRef[b] = smoothedRef[b] * 0.7 + rawBuckets[b] * 0.3;
        }

        // Handy 3-point spatial smoothing to eliminate visual jitter
        const finalLevels = Array(9).fill(0);
        for (let b = 0; b < 9; b++) {
          const prev = b > 0 ? smoothedRef[b - 1] : smoothedRef[b];
          const next = b < 8 ? smoothedRef[b + 1] : smoothedRef[b];
          finalLevels[b] = smoothedRef[b] * 0.7 + prev * 0.15 + next * 0.15;
        }

        setWaveLevels(finalLevels);

        const avgLevel = finalLevels.reduce((a, b) => a + b, 0) / 9;
        setAudioLevel(Math.min(100, Math.round(avgLevel * 100)));

        // Digital silence detection (Handy MicrophoneSilent pattern):
        // If unmuted and total frequency power is negligible (< 10) for > 90 frames (~1.5s), warn user
        if (totalPower < 10) {
          silentFrames++;
          if (silentFrames > 90) {
            setIsMicSilent(true);
          }
        } else {
          silentFrames = 0;
          setIsMicSilent(false);
        }

        animFrameRef.current = requestAnimationFrame(checkVolume);
      };
      animFrameRef.current = requestAnimationFrame(checkVolume);
    } catch (e) {
      console.warn('AudioContext analyser not supported:', e);
    }
  };

  // Terminate & Transition to Rating
  const handleCallEnded = useCallback(
    (_reason?: string) => {
      cleanupMedia();
      setCallState('ended');
      setActiveCallId((currentId) => {
        if (currentId) {
          setLastCallId(currentId);
          setShowRating(true);
        }
        return null;
      });
      setPeerInfo(null);
      setCallRole(null);
      loadStatus();
    },
    [cleanupMedia, loadStatus]
  );

  // Start WebRTC Connection
  const initializeWebRtc = useCallback(
    async (callId: string, role: 'offerer' | 'answerer', iceServers: RTCIceServer[]) => {
      const sessionId = ++callSessionRef.current;
      try {
        setCallState('connecting');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        if (callSessionRef.current !== sessionId) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        localStreamRef.current = stream;
        startAudioAnalyser(stream);

        const pc = new RTCPeerConnection({
          iceServers: iceServers.length > 0 ? iceServers : [{ urls: 'stun:stun.l.google.com:19302' }],
        });
        peerConnectionRef.current = pc;

        stream.getTracks().forEach((track) => {
          pc.addTrack(track, stream);
        });

        pc.ontrack = (event) => {
          if (callSessionRef.current !== sessionId) return;
          if (remoteAudioRef.current && event.streams[0]) {
            remoteAudioRef.current.srcObject = event.streams[0];
            remoteAudioRef.current.play().catch(() => {});
          }
        };

        pc.onicecandidate = (event) => {
          if (callSessionRef.current !== sessionId) return;
          if (event.candidate) {
            realtime.send({
              action: 'voice.call_ice_candidate',
              call_id: callId,
              candidate: event.candidate,
            });
          }
        };

        pc.onconnectionstatechange = () => {
          if (callSessionRef.current !== sessionId) return;
          if (pc.connectionState === 'connected') {
            setCallState('in_call');
            setSecondsRemaining(600);
            if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
            countdownIntervalRef.current = window.setInterval(() => {
              setSecondsRemaining((prev) => {
                if (prev <= 1) {
                  clearInterval(countdownIntervalRef.current!);
                  return 0;
                }
                return prev - 1;
              });
            }, 1000);

            realtime.send({ action: 'voice.call_connected', call_id: callId });
          } else if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
            if (callStateRef.current === 'in_call' || callStateRef.current === 'connecting') {
              handleCallEnded('connection_dropped');
            }
          }
        };

        if (role === 'offerer') {
          const offer = await pc.createOffer();
          if (callSessionRef.current !== sessionId) return;
          await pc.setLocalDescription(offer);
          realtime.send({
            action: 'voice.call_offer',
            call_id: callId,
            sdp: offer.sdp,
          });
        } else if (role === 'answerer' && pendingOfferRef.current) {
          const offerData = pendingOfferRef.current;
          pendingOfferRef.current = null;
          await pc.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: offerData.sdp }));
          if (callSessionRef.current !== sessionId) return;
          const answer = await pc.createAnswer();
          if (callSessionRef.current !== sessionId) return;
          await pc.setLocalDescription(answer);
          realtime.send({
            action: 'voice.call_answer',
            call_id: callId,
            sdp: answer.sdp,
          });
          await flushPendingCandidates(pc);
        }
      } catch (err: any) {
        if (callSessionRef.current !== sessionId) return;
        let detail = err?.message || 'permissions required';
        if (err?.name === 'NotAllowedError') {
          detail = 'Zezwolenie na mikrofon zostało odrzucone / Permission denied';
        } else if (err?.name === 'NotFoundError') {
          detail = 'Nie znaleziono mikrofonu / No microphone device found';
        } else if (err?.name === 'NotReadableError') {
          detail = 'Urządzenie audio zajęte / Audio device in use';
        }
        setErrorMsg(vcopy.micError(detail));
        setCallState('idle');
        cleanupMedia();
      }
    },
    [cleanupMedia, handleCallEnded, vcopy]
  );

  // WebSocket Event Listeners
  useEffect(() => {
    const unsubMatched = realtime.on('voice.call_matched', async (payload: any, env: any) => {
      const data = env?.call_id ? env : payload;
      if (!data || !data.call_id) return;

      const reducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
      if (!reducedMotion) {
        try {
          navigator.vibrate?.(120);
          const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
          if (AudioCtx) {
            const ctx = new AudioCtx();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(523.25, ctx.currentTime);
            osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.11);
            gain.gain.setValueAtTime(0.06, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.28);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.3);
            setTimeout(() => ctx.close().catch(() => {}), 350);
          }
        } catch {
          // Ignore audio chime failure if autoplay is restricted
        }
      }

      setActiveCallId(data.call_id);
      setCallRole(data.role);
      setPeerInfo(data.peer);

      const iceServers = data.ice_servers || [];
      await initializeWebRtc(data.call_id, data.role, iceServers);
    });

    const unsubOffer = realtime.on('voice.call_offer', async (payload: any, env: any) => {
      const data = env?.sdp ? env : payload;
      if (!data?.sdp) return;
      const pc = peerConnectionRef.current;
      if (pc) {
        try {
          await pc.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: data.sdp }));
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          realtime.send({
            action: 'voice.call_answer',
            call_id: data.call_id || activeCallIdRef.current,
            sdp: answer.sdp,
          });
          await flushPendingCandidates(pc);
        } catch (e) {
          console.error('Error handling offer:', e);
        }
      } else {
        pendingOfferRef.current = data;
      }
    });

    const unsubAnswer = realtime.on('voice.call_answer', async (payload: any, env: any) => {
      const data = env?.sdp ? env : payload;
      const pc = peerConnectionRef.current;
      if (pc && data?.sdp) {
        try {
          await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: data.sdp }));
          await flushPendingCandidates(pc);
        } catch (e) {
          console.error('Error handling answer:', e);
        }
      }
    });

    const unsubIce = realtime.on('voice.call_ice_candidate', async (payload: any, env: any) => {
      const data = env?.candidate ? env : payload;
      if (!data?.candidate) return;
      const pc = peerConnectionRef.current;
      if (pc && pc.remoteDescription) {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
        } catch (e) {
          console.error('Error adding ICE candidate:', e);
        }
      } else {
        pendingCandidatesRef.current.push(data.candidate);
      }
    });

    const unsubTimeout = realtime.on('voice.queue_timeout', (payload: any, env: any) => {
      const msg = env?.message || payload?.message || vcopy.noCallers;
      setErrorMsg(msg);
      setCallState('idle');
    });

    const unsubCallEnded = realtime.on('voice.call_ended', (payload: any, env: any) => {
      const reason = env?.reason || payload?.reason || 'completed';
      handleCallEnded(reason);
    });

    return () => {
      unsubMatched();
      unsubOffer();
      unsubAnswer();
      unsubIce();
      unsubTimeout();
      unsubCallEnded();
    };
  }, [initializeWebRtc, handleCallEnded, vcopy.noCallers]);

  // Mute / Unmute
  const toggleMute = () => {
    if (localStreamRef.current) {
      const tracks = localStreamRef.current.getAudioTracks();
      tracks.forEach((track) => {
        track.enabled = !track.enabled;
      });
      setIsMuted(!tracks[0]?.enabled);
    }
  };

  // Join Matchmaking Queue
  const handleJoinQueue = () => {
    if (!token) return;
    setErrorMsg(null);
    setCallState('searching');
    realtime.send({
      action: 'voice.join_queue',
      topic: selectedTopic,
    });
  };

  // Leave Matchmaking Queue
  const handleLeaveQueue = () => {
    setCallState('idle');
    realtime.send({ action: 'voice.leave_queue' });
  };

  // Hangup Call (single authoritative call path with WS fallback; zero duplicate hangup requests)
  const handleHangup = async (blockPeer = false) => {
    setShowBlockConfirm(false);
    if (activeCallId && token) {
      try {
        await hangupVoiceCall(activeCallId, token, blockPeer);
      } catch (e) {
        console.warn('Hangup REST error, falling back to WS:', e);
        realtime.send({
          action: 'voice.call_hangup',
          call_id: activeCallId,
          reason: blockPeer ? 'user_blocked' : 'user_hangup',
          block_peer: blockPeer,
        });
      }
    }
    handleCallEnded(blockPeer ? 'user_blocked' : 'user_hangup');
  };

  // Submit Rating
  const handleSubmitRating = async () => {
    if (!lastCallId || !token) {
      setShowRating(false);
      return;
    }
    try {
      await rateVoiceCall(
        lastCallId,
        {
          rating: selectedRating,
          details: ratingDetails.trim() || undefined,
          block_peer: ratingBlockPeer,
        },
        token
      );
      setRatingSubmitted(true);
      setTimeout(() => {
        setShowRating(false);
        setRatingSubmitted(false);
        setLastCallId(null);
        setRatingDetails('');
        setRatingBlockPeer(false);
      }, 1500);
    } catch (err: any) {
      setErrorMsg(vcopy.errorRating + (err.message || ''));
    }
  };

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-64px)] bg-slate-950 text-slate-100 p-4 max-w-lg mx-auto pb-24">
      {/* Hidden remote audio element */}
      <audio ref={remoteAudioRef} autoPlay playsInline />

      {/* Header / Notice */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <PhoneCall className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white leading-tight">
              {vcopy.title}
            </h1>
            <p className="text-xs text-slate-400">
              {vcopy.subtitle}
            </p>
          </div>
        </div>

        <button
          onClick={loadStatus}
          disabled={loading}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition cursor-pointer"
          title={vcopy.refresh}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {errorMsg && (
        <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-2.5 text-xs text-rose-300">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 font-bold hover:text-rose-200">
            ✕
          </button>
        </div>
      )}

      {/* --- State 1: Active In-Call HUD --- */}
      {(callState === 'in_call' || callState === 'connecting') && (
        <div className="flex-1 flex flex-col items-center justify-between py-6">
          {/* Peer & Safety info */}
          <div className="w-full text-center">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium mb-3">
              <Lock className="w-3.5 h-3.5 text-indigo-400" />
              {vcopy.encryptedNotice}
            </span>
            <h2 className="text-2xl font-black text-white">
              {peerInfo ? `${peerInfo.first_name} (${peerInfo.city})` : vcopy.connectingPeer}
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto line-clamp-2">
              {vcopy.topicLabel} <span className="text-slate-200 font-semibold">{selectedTopic}</span>
            </p>
          </div>

          {/* Large Countdown Timer & Pulse Wave */}
          <div className="my-8 flex flex-col items-center justify-center relative">
            {/* Glowing audio activity ring */}
            <div
              className="absolute w-44 h-44 rounded-full border-2 border-indigo-500/20 transition-transform duration-75 ease-out"
              style={{
                transform: `scale(${1 + (waveLevels.reduce((a, b) => a + b, 0) / 9) * 0.25})`,
                borderColor: audioLevel > 15 ? 'rgba(99, 102, 241, 0.7)' : 'rgba(99, 102, 241, 0.2)',
                boxShadow:
                  audioLevel > 15
                    ? `0 0 ${audioLevel / 2}px rgba(99, 102, 241, 0.5)`
                    : 'none',
              }}
            />

            <div className="w-36 h-36 rounded-full bg-slate-900/90 border border-slate-800 flex flex-col items-center justify-center z-10 shadow-2xl glass-panel">
              <Clock
                className={`w-5 h-5 mb-0.5 ${
                  secondsRemaining <= 60 ? 'text-amber-400 animate-pulse' : 'text-indigo-400'
                }`}
              />
              <span
                className={`text-3xl font-black tracking-tight ${
                  secondsRemaining <= 60 ? 'text-amber-400' : 'text-white'
                }`}
              >
                {formatTimer(secondsRemaining)}
              </span>

              {/* Dynamic Equalizer Wave Bars (Handy 9-bar logarithmic speech visualizer) */}
              <div className="flex items-center gap-0.5 h-4 my-1">
                {waveLevels.map((lvl, idx) => (
                  <span
                    key={idx}
                    className={`w-0.5 rounded-full transition-all duration-75 ${
                      idx === 4 ? 'bg-violet-400' : idx % 2 === 0 ? 'bg-indigo-400' : 'bg-indigo-300'
                    }`}
                    style={{
                      height: `${Math.max(3, Math.min(16, Math.round(3 + Math.pow(lvl, 0.7) * 13)))}px`,
                    }}
                  />
                ))}
              </div>

              <span className="text-[9px] text-slate-500 uppercase tracking-wider font-bold">
                {vcopy.limit10}
              </span>
            </div>

            {/* Digital silence / hardware mute warning badge (Handy MicrophoneSilent pattern) */}
            {isMicSilent && !isMuted && callState === 'in_call' && (
              <div
                role="alert"
                className="mt-3 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-lg py-1 px-3 flex items-center justify-center gap-1.5 animate-pulse z-10"
              >
                <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span>{vcopy.micSilentWarning}</span>
              </div>
            )}

            {/* Milestone-only screen-reader announcer (5:00, 1:00, 0:30) */}
            <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
              {milestoneAnnouncement}
            </div>
          </div>

          {/* Icebreaker Prompt Cards with quick shuffle */}
          <div className="w-full bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4 mb-6 shadow-md glass-panel">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2">
              <span className="flex items-center gap-1.5 text-amber-300 font-bold">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                {vcopy.icebreakerPrompt}
              </span>
              <button
                type="button"
                onClick={() => {
                  const list = statusData?.icebreakers || [];
                  if (list.length > 0) {
                    const currentIndex = list.indexOf(selectedTopic);
                    const nextTopic = list[(currentIndex + 1) % list.length];
                    setSelectedTopic(nextTopic);
                  }
                }}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className="w-3 h-3" />
                {vcopy.anotherQuestion}
              </button>
            </div>
            <p className="text-xs text-slate-200 italic leading-relaxed">
              "{selectedTopic}"
            </p>
          </div>

          {/* In-Call Controls */}
          <div className="w-full flex items-center justify-center gap-3">
            {/* Mute Button */}
            <button
              onClick={toggleMute}
              className={`flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition cursor-pointer ${
                isMuted
                  ? 'bg-amber-500/20 border border-amber-500/40 text-amber-400'
                  : 'bg-slate-800/90 border border-slate-700 text-slate-200 hover:text-white'
              }`}
              title={isMuted ? vcopy.unmuteMic : vcopy.muteMic}
            >
              {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
              <span className="text-[10px] mt-1 font-medium">{isMuted ? vcopy.micOffLabel : vcopy.micOnLabel}</span>
            </button>

            {/* Speakerphone / Output Switcher Button (Handy audio output device switcher pattern) */}
            <button
              onClick={toggleSpeakerphone}
              className={`flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition cursor-pointer ${
                isSpeakerphone
                  ? 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-400'
                  : 'bg-slate-800/90 border border-slate-700 text-slate-200 hover:text-white'
              }`}
              title={isSpeakerphone ? vcopy.speakerOnLabel : vcopy.speakerOffLabel}
            >
              <Volume2 className="w-6 h-6" />
              <span className="text-[10px] mt-1 font-medium">{isSpeakerphone ? vcopy.speakerOnLabel : vcopy.speakerOffLabel}</span>
            </button>

            {/* Red Hangup Button */}
            <button
              onClick={() => handleHangup(false)}
              className="flex flex-col items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-rose-600 to-rose-500 text-white shadow-lg shadow-rose-600/30 hover:scale-105 transition cursor-pointer"
              title={vcopy.endCallTitle}
            >
              <PhoneOff className="w-7 h-7" />
              <span className="text-[10px] mt-0.5 font-bold">{vcopy.endLabel}</span>
            </button>

            {/* End & Block Button */}
            <button
              onClick={() => setShowBlockConfirm(true)}
              className="flex flex-col items-center justify-center w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 text-rose-400 hover:bg-rose-950/30 hover:border-rose-800 transition cursor-pointer"
              title={vcopy.endBlockTitle}
            >
              <ShieldAlert className="w-6 h-6" />
              <span className="text-[10px] mt-1 font-medium">{vcopy.blockLabel}</span>
            </button>
          </div>

          {/* Block Confirmation Dialog */}
          {showBlockConfirm && (
            <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
              <div
                id="voice-block-confirm-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby="voice-block-confirm-title"
                tabIndex={-1}
                className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 text-center"
              >
                <ShieldAlert className="w-10 h-10 text-rose-400 mx-auto mb-3" />
                <h3 id="voice-block-confirm-title" className="text-base font-bold text-white mb-2">{vcopy.blockConfirmTitle}</h3>
                <p className="text-xs text-slate-300 leading-relaxed mb-5">
                  {vcopy.blockConfirmBody}
                </p>
                <div className="flex gap-2.5">
                  <button
                    onClick={() => setShowBlockConfirm(false)}
                    className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition"
                  >
                    {vcopy.cancel}
                  </button>
                  <button
                    onClick={() => handleHangup(true)}
                    className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition shadow-lg shadow-rose-600/30"
                  >
                    {vcopy.blockNow}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* --- State 2: Searching / In Queue --- */}
      {callState === 'searching' && (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
          <div className="relative mb-8">
            <div className="w-28 h-28 rounded-full border-2 border-indigo-500/30 animate-ping absolute inset-0" />
            <div className="w-28 h-28 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center shadow-xl shadow-indigo-600/30 relative z-10">
              <PhoneCall className="w-10 h-10 text-white animate-pulse" />
            </div>
          </div>

          <h3 className="text-lg font-bold text-white mb-2">{vcopy.searchingTitle}</h3>
          <p className="text-xs text-slate-400 max-w-xs mb-4">
            {vcopy.searchingBody}
          </p>

          <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-300 mb-8 max-w-xs">
            {vcopy.topicLabel} <span className="font-semibold text-indigo-300">{selectedTopic}</span>
          </div>

          <button
            onClick={handleLeaveQueue}
            className="px-6 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold transition cursor-pointer"
          >
            {vcopy.cancelSearch}
          </button>
        </div>
      )}

      {/* --- State 3: Lobby / Idle --- */}
      {callState === 'idle' && (
        <div className="flex-1 flex flex-col gap-5">
          {/* Schedule & Quota Widget */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400">{vcopy.windowStatus}</span>
              {statusData?.window_open ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {vcopy.windowOpen}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  {vcopy.windowClosed}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1 border-t border-slate-800/60">
              <div>
                <span className="text-[11px] text-slate-500 block">{vcopy.callsUsedToday}</span>
                <span className="text-sm font-bold text-slate-200">
                  {statusData ? `${statusData.daily_calls_used} / ${statusData.daily_limit}` : '0 / 3'}
                </span>
              </div>
              <div>
                <span className="text-[11px] text-slate-500 block">{vcopy.cooldownLabel}</span>
                <span className="text-sm font-bold text-slate-200">
                  {statusData?.cooldown_remaining_seconds ? (
                    <span className="text-amber-400">{statusData.cooldown_remaining_seconds}s</span>
                  ) : (
                    vcopy.cooldownNone
                  )}
                </span>
              </div>
            </div>
          </div>

          {/* Privacy & Safe Rules Card */}
          <div className="bg-gradient-to-tr from-slate-900 to-indigo-950/40 border border-indigo-950/80 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold text-xs">
              <ShieldAlert className="w-4 h-4" />
              <span>{vcopy.safeSpaceTitle}</span>
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li>{vcopy.safeRule1}</li>
              <li>{vcopy.safeRule2}</li>
              <li>{vcopy.safeRule3}</li>
              <li>{vcopy.safeRule4}</li>
            </ul>
          </div>

          {/* Topic Picker */}
          <div>
            <label className="text-xs font-bold text-slate-300 block mb-2">
              {vcopy.chooseTopic}
            </label>
            <div className="space-y-2">
              {(statusData?.icebreakers || [
                vcopy.defaultTopic1,
                vcopy.defaultTopic2,
                vcopy.defaultTopic3,
              ]).map((topic, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedTopic(topic)}
                  className={`w-full text-left px-3.5 py-3 rounded-xl border text-xs transition cursor-pointer ${
                    selectedTopic === topic
                      ? 'bg-indigo-600/15 border-indigo-500 text-white font-medium shadow-sm'
                      : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  {topic}
                </button>
              ))}
            </div>
          </div>

          {/* Connect Button */}
          <div className="mt-auto pt-4">
            <button
              onClick={handleJoinQueue}
              disabled={
                Boolean(statusData && !statusData.window_open) ||
                Boolean(statusData?.cooldown_remaining_seconds && statusData.cooldown_remaining_seconds > 0) ||
                Boolean(statusData?.daily_calls_used && statusData.daily_calls_used >= 3)
              }
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white font-bold text-sm shadow-xl shadow-indigo-600/25 flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PhoneCall className="w-5 h-5" />
              <span>
                {statusData?.cooldown_remaining_seconds && statusData.cooldown_remaining_seconds > 0
                  ? vcopy.cooldownButton(statusData.cooldown_remaining_seconds)
                  : statusData && !statusData.window_open
                  ? vcopy.windowClosedButton
                  : statusData?.daily_calls_used && statusData.daily_calls_used >= 3
                  ? vcopy.dailyLimitReached
                  : vcopy.connectNow}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* --- Post-Call Rating Modal --- */}
      {showRating && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            id="voice-rating-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="voice-rating-title"
            tabIndex={-1}
            className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 text-center"
          >
            {ratingSubmitted ? (
              <div className="py-8">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                <h3 id="voice-rating-title" className="text-base font-bold text-white">{vcopy.rateThanks}</h3>
                <p className="text-xs text-slate-400 mt-1">{vcopy.ratingHelps}</p>
              </div>
            ) : (
              <>
                <h3 id="voice-rating-title" className="text-base font-bold text-white mb-1">{vcopy.rateTitle}</h3>
                <p className="text-xs text-slate-400 mb-4">{vcopy.ratingAnonymous}</p>

                <div className="grid grid-cols-3 gap-2 mb-4">
                  <button
                    onClick={() => setSelectedRating('respectful')}
                    className={`py-3 px-2 rounded-xl border flex flex-col items-center gap-1 transition cursor-pointer ${
                      selectedRating === 'respectful'
                        ? 'bg-emerald-500/15 border-emerald-500 text-emerald-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <span className="text-xl">💚</span>
                    <span className="text-[11px] font-bold">{vcopy.ratingRespectful}</span>
                  </button>

                  <button
                    onClick={() => setSelectedRating('neutral')}
                    className={`py-3 px-2 rounded-xl border flex flex-col items-center gap-1 transition cursor-pointer ${
                      selectedRating === 'neutral'
                        ? 'bg-indigo-500/15 border-indigo-500 text-indigo-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <span className="text-xl">😐</span>
                    <span className="text-[11px] font-bold">{vcopy.ratingNeutral}</span>
                  </button>

                  <button
                    onClick={() => setSelectedRating('inappropriate')}
                    className={`py-3 px-2 rounded-xl border flex flex-col items-center gap-1 transition cursor-pointer ${
                      selectedRating === 'inappropriate'
                        ? 'bg-rose-500/15 border-rose-500 text-rose-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <span className="text-xl">🚩</span>
                    <span className="text-[11px] font-bold">{vcopy.ratingInappropriate}</span>
                  </button>
                </div>

                <textarea
                  value={ratingDetails}
                  onChange={(e) => setRatingDetails(e.target.value)}
                  placeholder={vcopy.ratingPlaceholder}
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 placeholder-slate-500 mb-3 focus:outline-none focus:border-indigo-500"
                />

                <label className="flex items-center gap-2 text-left text-xs text-slate-400 mb-5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ratingBlockPeer}
                    onChange={(e) => setRatingBlockPeer(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-950 text-indigo-500 focus:ring-0"
                  />
                  <span>{vcopy.ratingBlock}</span>
                </label>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowRating(false)}
                    className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-400 text-xs font-semibold hover:bg-slate-700 transition"
                  >
                    {vcopy.ratingSkip}
                  </button>
                  <button
                    onClick={handleSubmitRating}
                    className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition shadow-lg shadow-indigo-600/30"
                  >
                    {vcopy.ratingSave}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceCallHUD;
