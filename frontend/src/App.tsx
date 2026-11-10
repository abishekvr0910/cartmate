import React, { useEffect, useState, useCallback } from 'react';
import {
  acceptJoinRequest,
  checkInTrip,
  completeTrip,
  createLivePing,
  fetchAllUsers,
  fetchCommunityStats,
  fetchCurrentUser,
  fetchMyAdmission,
  fetchModerationAccess,
  createPilotAgeCheckChallenge,
  fetchLivePings,
  fetchActiveTrip,
  logoutUser,
  requestToJoinPing,
  switchUser,
  toggleSafeHaven,
  triggerTripSos,
  verifyId,
  POLISH_CITIES,
  getStoredToken,
} from './api';
import { realtime } from './realtime/socket';
import { ActiveTripHUD } from './components/ActiveTripHUD';
import { BottomNav } from './components/BottomNav';
import type { NavTab } from './components/BottomNav';
import { CreatePingModal } from './components/CreatePingModal';
import { Header } from './components/Header';
import { LiveRadarView } from './components/LiveRadarView';
import { ProfileView } from './components/ProfileView';
import { SafetyHub } from './components/SafetyHub';
import { AuthModal } from './components/AuthModal';
import { PrivacyBanner } from './components/PrivacyBanner';
import { PilotAgeConsole } from './components/PilotAgeConsole';
import { PodFeed } from './components/PodFeed';
import { VoiceCallHUD } from './components/VoiceCallHUD';
import { Users, Sparkles, PhoneCall } from 'lucide-react';
import type { ChatMessage, CommunityStats, LivePing, Trip, User } from './types';
import type { Language } from './locales';
import { translations } from './locales';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [pings, setPings] = useState<LivePing[]>([]);
  const [activeTrip, setActiveTrip] = useState<Trip | null>(null);
  const [hasNewChatActivity, setHasNewChatActivity] = useState(false);
  const [tripCancelledNotice, setTripCancelledNotice] = useState(false);
  const [stats, setStats] = useState<CommunityStats | null>(null);

  // Defaults to Polish ('pl') and Silesia hub ('Katowice') for launch!
  const [lang, setLang] = useState<Language>('pl');
  const [activeTab, setActiveTab] = useState<NavTab>('radar');
  const [selectedCity, setSelectedCity] = useState<string>('Katowice');
  const [isMobileFrame, setIsMobileFrame] = useState<boolean>(false);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [initError, setInitError] = useState<string | null>(null);
  const [ageBlocked, setAgeBlocked] = useState(false);
  const [pilotAgeChallengeAvailable, setPilotAgeChallengeAvailable] = useState(false);
  const [ageChallenge, setAgeChallenge] = useState<{ challenge: string; expires_at: string } | null>(null);
  const [ageChallengeError, setAgeChallengeError] = useState<string | null>(null);
  const [canModerateAge, setCanModerateAge] = useState(false);
  const isCityInitialized = React.useRef(false);
  const selectedCityRef = React.useRef(selectedCity);
  const activeTabRef = React.useRef(activeTab);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    if (!currentUser || !ageBlocked) return;
    let cancelled = false;
    void fetchModerationAccess().then((allowed) => {
      if (!cancelled) setCanModerateAge(allowed);
    }).catch(() => {
      if (!cancelled) setCanModerateAge(false);
    });
    return () => { cancelled = true; };
  }, [currentUser, ageBlocked]);

  useEffect(() => {
    selectedCityRef.current = selectedCity;
  }, [selectedCity]);

  useEffect(() => {
    activeTabRef.current = activeTab;
    // oxlint-disable-next-line react/set-state-in-effect
    if (activeTab === 'active_trip') setHasNewChatActivity(false);
  }, [activeTab]);

  const getCityCoords = useCallback((cityName: string) => {
    const found = POLISH_CITIES.find(
      (c) => c.name.toLowerCase() === cityName.toLowerCase()
    );
    return found || { name: 'Katowice', lat: 50.2649, lng: 19.0238 };
  }, []);

  // Initial load: Only runs on mount or retry, does not overwrite manually selected cities
  const loadInitialData = useCallback(async (targetCity?: string) => {
    const city = targetCity ?? selectedCity;
    try {
      setLoading(true);
      setInitError(null);
      if (!getStoredToken()) {
        setCanModerateAge(false);
        setPilotAgeChallengeAvailable(false);
        setAgeChallenge(null);
        setCurrentUser(null);
        setAgeBlocked(false);
        setAllUsers([]);
        setPings([]);
        setActiveTrip(null);
        setIsAuthModalOpen(true);
        return false;
      }
      const user = await fetchCurrentUser();
      const admission = await fetchMyAdmission();
      setCurrentUser(user);
      setAgeBlocked(!admission.live_access);
      setPilotAgeChallengeAvailable(admission.manual_age_check_available === true);
      if (!admission.live_access) {
        setAllUsers([]);
        setPings([]);
        setActiveTrip(null);
        return false;
      }
      const coords = getCityCoords(city);
      const [users, livePings, trip, communityStats] = await Promise.all([
        fetchAllUsers(),
        fetchLivePings({ userLat: coords.lat, userLng: coords.lng }),
        fetchActiveTrip(),
        fetchCommunityStats(),
      ]);
      setCurrentUser(user);
      if (!isCityInitialized.current && user.city) {
        setSelectedCity(user.city);
        isCityInitialized.current = true;
      }
      setAllUsers(users);
      setPings(livePings);
      setActiveTrip(trip);
      if (trip && ['scheduled', 'in_progress'].includes(trip.status)) {
        setActiveTab('active_trip');
      }
      setStats(communityStats);
      const storedToken = getStoredToken();
      if (storedToken && admission.live_access) {
        realtime.connect(storedToken);
        realtime.subscribe(`city:${(user.city || city).toLowerCase()}`);
      }
      return true;
    } catch (err: any) {
      console.error('Error loading initial data:', err);
      if (!getStoredToken()) {
        setCurrentUser(null);
        setActiveTrip(null);
        setIsAuthModalOpen(true);
        return false;
      }
      setInitError(err.message || 'Nie udało się połączyć z serwerem CartMate.');
      return false;
    } finally {
      setLoading(false);
    }
  }, [getCityCoords, selectedCity]);

  useEffect(() => {
    let isCancelled = false;
    let fallbackInterval: number | null = null;

    const stopFallbackPolling = () => {
      if (fallbackInterval !== null) {
        clearInterval(fallbackInterval);
        fallbackInterval = null;
      }
    };

    const startFallbackPolling = () => {
      if (fallbackInterval !== null || isCancelled) return;
      fallbackInterval = window.setInterval(async () => {
        if (isCancelled) return;
        if (realtime.isConnected()) {
          stopFallbackPolling();
          return;
        }
        try {
          if (!getStoredToken()) return;
          const coords = getCityCoords(selectedCityRef.current);
          const [updatedPings, currentTrip] = await Promise.all([
            fetchLivePings({ userLat: coords.lat, userLng: coords.lng }),
            fetchActiveTrip(),
          ]);
          if (!isCancelled) {
            setPings(updatedPings);
            setActiveTrip(currentTrip);
          }
        } catch (e) {
          console.error('Background fallback refresh error:', e);
        }
      }, 30000);
    };

    void (async () => {
      const liveAccess = await loadInitialData();
      const token = getStoredToken();
      if (token && liveAccess) {
        realtime.connect(token);
      }
    })();

    const rehydrateAuthorizedState = () => {
      if (!getStoredToken()) return;
      const coords = getCityCoords(selectedCityRef.current);
      void Promise.all([
        fetchLivePings({ userLat: coords.lat, userLng: coords.lng }),
        fetchActiveTrip(),
      ]).then(([updatedPings, currentTrip]) => {
        if (!isCancelled) {
          setPings(updatedPings);
          setActiveTrip((prev) => {
            if (currentTrip) {
              return prev?.id === currentTrip.id
                ? { ...currentTrip, host_pin: prev.host_pin ?? currentTrip.host_pin }
                : currentTrip;
            } else if (prev) {
              setTripCancelledNotice(true);
              return null;
            }
            return null;
          });
        }
      }).catch((error) => console.error('Could not rehydrate state on reconnect:', error));
    };

    // Status listener: when WebSocket is active and healthy, zero polling runs
    const unsubStatus = realtime.onStatusChange((status) => {
      if (status === 'connected') {
        stopFallbackPolling();
        rehydrateAuthorizedState();
      } else if (status === 'disconnected') {
        startFallbackPolling();
      }
    });

    const unsubConnectionReady = realtime.on('connection.ready', () => {
      rehydrateAuthorizedState();
    });

    // Setup real-time event listeners
    const unsubPingCreated = realtime.on('ping.created', () => {
      if (!getStoredToken()) return;
      const coords = getCityCoords(selectedCityRef.current);
      void fetchLivePings({ userLat: coords.lat, userLng: coords.lng })
        .then((visiblePings) => {
          if (!isCancelled) setPings(visiblePings);
        })
        .catch((error) => console.error('Could not refresh nearby outings:', error));
    });

    // Shared trip frames cannot contain the host-only PIN. Retain a PIN that
    // this participant already received from their authorized REST response.
    const applySharedTripUpdate = (updatedTrip: Trip) => {
      setActiveTrip((current) => current?.id === updatedTrip.id
        ? { ...updatedTrip, host_pin: current.host_pin ?? updatedTrip.host_pin }
        : updatedTrip);
    };

    const unsubTripUpdated = realtime.on('trip.status_updated', (updatedTrip: Trip) => {
      applySharedTripUpdate(updatedTrip);
    });

    const unsubHandshake = realtime.on('trip.handshake_verified', (updatedTrip: Trip) => {
      applySharedTripUpdate(updatedTrip);
    });

    const unsubSos = realtime.on('trip.sos_triggered', (updatedTrip: Trip) => {
      applySharedTripUpdate(updatedTrip);
    });
    const unsubTripCancelled = realtime.on<{ trip_id: string }>('trip.cancelled', (event) => {
      setActiveTrip((current) => current?.id === event.trip_id ? null : current);
      setTripCancelledNotice(true);
    });

    const unsubTripCreated = realtime.on('trip.created', (newTrip: Trip) => {
      applySharedTripUpdate(newTrip);
      setActiveTab('active_trip');
    });
    const unsubPlanUpdated = realtime.on('trip.plan_updated', (updatedTrip: Trip) => {
      applySharedTripUpdate(updatedTrip);
    });
    const unsubPlanAccepted = realtime.on('trip.plan_accepted', (updatedTrip: Trip) => {
      applySharedTripUpdate(updatedTrip);
    });

    return () => {
      isCancelled = true;
      stopFallbackPolling();
      unsubStatus();
      unsubConnectionReady();
      unsubPingCreated();
      unsubTripUpdated();
      unsubHandshake();
      unsubSos();
      unsubTripCancelled();
      unsubTripCreated();
      unsubPlanUpdated();
      unsubPlanAccepted();
    };
  }, [getCityCoords, loadInitialData]);

  // Keep the participant's trip scope active across tabs, including when the
  // chat HUD is closed. This lets plan, SOS and cancellation updates arrive.
  useEffect(() => {
    if (!activeTrip?.id) return;
    const scope = `trip:${activeTrip.id}`;
    realtime.subscribe(scope);
    return () => realtime.unsubscribe(scope);
  }, [activeTrip?.id]);

  // Keep the private chat scope while visiting other tabs. This is a quiet,
  // session-only cue, not a server read receipt or a push notification.
  const chatRoomId = activeTrip?.chat_room_id;
  const currentUserId = currentUser?.id;
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    setHasNewChatActivity(false);
    if (!chatRoomId || !currentUserId) return;
    const scope = `chat:${chatRoomId}`;
    const unsubscribeMessage = realtime.on<ChatMessage>('chat.message', (message) => {
      if (message.chat_room_id === chatRoomId
        && message.sender_id !== currentUserId
        && activeTabRef.current !== 'active_trip') {
        setHasNewChatActivity(true);
      }
    });
    realtime.subscribe(scope);
    return () => {
      unsubscribeMessage();
      realtime.unsubscribe(scope);
    };
  }, [chatRoomId, currentUserId]);

  const handleSelectCity = async (cityName: string) => {
    setSelectedCity(cityName);
    realtime.subscribe(`city:${cityName.toLowerCase()}`);
    try {
      const coords = getCityCoords(cityName);
      const updatedPings = await fetchLivePings({ userLat: coords.lat, userLng: coords.lng });
      setPings(updatedPings);
    } catch (e) {
      console.error('Failed to fetch pings for city:', e);
    }
  };

  const handleAuthSuccess = async (user: User) => {
    const token = getStoredToken();
    if (!token) {
      setInitError('Logowanie nie zwrÃ³ciÅ‚o waÅ¼nej sesji. SprÃ³buj ponownie.');
      return;
    }
    setInitError(null);
    setCanModerateAge(false);
    setAgeChallenge(null);
    setIsAuthModalOpen(false);
    setCurrentUser(user);
    if (user.city) {
      setSelectedCity(user.city);
    }
    const admission = await fetchMyAdmission().catch(() => null);
    setAgeBlocked(!admission?.live_access);
    setPilotAgeChallengeAvailable(admission?.manual_age_check_available === true);
    if (!admission?.live_access) {
      setAllUsers([]);
      setPings([]);
      setActiveTrip(null);
      return;
    }
    realtime.connect(token);
    realtime.subscribe(`city:${(user.city || selectedCity).toLowerCase()}`);

    const coords = getCityCoords(user.city || selectedCity);
    const [updatedPings, currentTrip, users] = await Promise.all([
      fetchLivePings({ userLat: coords.lat, userLng: coords.lng }),
      fetchActiveTrip(),
      fetchAllUsers(),
    ]);
    setPings(updatedPings);
    setActiveTrip(currentTrip);
    setAllUsers(users);
  };

  const handleLogout = async () => {
    realtime.disconnect();
    await logoutUser();
    setHasNewChatActivity(false);
    setCurrentUser(null);
    setActiveTrip(null);
    setTripCancelledNotice(false);
    setPings([]);
    setAllUsers([]);
    setStats(null);
    setInitError(null);
    setAgeBlocked(false);
    setPilotAgeChallengeAvailable(false);
    setAgeChallenge(null);
    setAgeChallengeError(null);
    setCanModerateAge(false);
    setIsAuthModalOpen(true);
  };

  const handleSwitchUser = async (userId: string) => {
    const updated = await switchUser(userId);
    await handleAuthSuccess(updated);
  };

  const handleCreateAgeChallenge = async () => {
    setAgeChallengeError(null);
    try {
      const issued = await createPilotAgeCheckChallenge();
      setAgeChallenge({ challenge: issued.challenge, expires_at: issued.expires_at });
    } catch (caught) {
      setAgeChallenge(null);
      setAgeChallengeError(caught instanceof Error ? caught.message : 'Could not create a check code.');
    }
  };

  const handleVerifyId = async () => {
    const updated = await verifyId();
    setCurrentUser(updated);
  };

  const handleToggleSafeHaven = async () => {
    const updated = await toggleSafeHaven();
    setCurrentUser(updated);
    const coords = getCityCoords(selectedCity);
    const updatedPings = await fetchLivePings({ userLat: coords.lat, userLng: coords.lng });
    setPings(updatedPings);
  };

  const handleCreatePing = async (data: any) => {
    await createLivePing(data);
    const coords = getCityCoords(selectedCity);
    const updatedPings = await fetchLivePings({ userLat: coords.lat, userLng: coords.lng });
    setPings(updatedPings);
    setActiveTab('radar');
  };

  const handleJoinPing = async (pingId: string, message: string) => {
    await requestToJoinPing(pingId, message);
    const coords = getCityCoords(selectedCity);
    const updatedPings = await fetchLivePings({ userLat: coords.lat, userLng: coords.lng });
    setPings(updatedPings);
  };

  const handleAcceptRequest = async (pingId: string, reqId: string) => {
    const spawnedTrip = await acceptJoinRequest(pingId, reqId);
    setActiveTrip(spawnedTrip);
    const coords = getCityCoords(selectedCity);
    const updatedPings = await fetchLivePings({ userLat: coords.lat, userLng: coords.lng });
    setPings(updatedPings);
    setActiveTab('active_trip');
  };

  const handleCheckIn = async (tripId: string) => {
    const updatedTrip = await checkInTrip(tripId);
    setActiveTrip(updatedTrip);
  };

  const handleTriggerSos = async (tripId: string) => {
    const updatedTrip = await triggerTripSos(tripId);
    setActiveTrip(updatedTrip);
  };

  const handleCompleteTrip = async (tripId: string) => {
    await completeTrip(tripId);
    setActiveTrip(null);
    const coords = getCityCoords(selectedCity);
    try {
      const [updatedUser, updatedPings, communityStats] = await Promise.all([
        fetchCurrentUser(),
        fetchLivePings({ userLat: coords.lat, userLng: coords.lng }),
        fetchCommunityStats(),
      ]);
      setCurrentUser(updatedUser);
      setPings(updatedPings);
      setStats(communityStats);
    } catch (error) {
      // Completion succeeded on the server. A secondary feed refresh failure
      // must not misreport that completed action as failed to the participant.
      console.error('Could not refresh the feed after completing the outing:', error);
    }
  };

  if (initError && !currentUser) {
    return (
      <div className="min-h-screen bg-[#0b0f19] flex items-center justify-center p-4">
        <div className="max-w-sm w-full bg-slate-900 border border-rose-500/30 rounded-3xl p-6 text-center space-y-4 shadow-2xl">
          <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center mx-auto text-2xl">
            ⚠️
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-bold text-white">
              {lang === 'pl' ? 'Problem z połączeniem' : lang === 'uk' ? 'Помилка з\'єднання' : lang === 'ru' ? 'Ошибка соединения' : 'Connection Error'}
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              {initError}
            </p>
          </div>
          <button
            onClick={() => { void loadInitialData(); }}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold text-xs hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-emerald-500/20 cursor-pointer"
          >
            {lang === 'pl' ? 'Spróbuj ponownie' : lang === 'uk' ? 'Спробувати знову' : lang === 'ru' ? 'Попробовать снова' : 'Retry Connection'}
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0f19] flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto animate-pulse">
            <span className="text-2xl font-black">C</span>
          </div>
          <p className="text-xs text-slate-400 font-semibold tracking-wider uppercase">
            Ładowanie radaru CartMate Polska...
          </p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <div className="min-h-screen bg-[#0b0f19] flex flex-col items-center justify-center p-6 text-center">
        <div className="space-y-2 mb-6">
          <h1 className="text-3xl font-black text-white">CartMate</h1>
          <p className="max-w-sm text-sm text-slate-400">
            {lang === 'pl'
              ? 'Codzienne sprawy raźniej robi się razem. Zaloguj się, aby odkrywać i planować spotkania.'
              : 'Everyday errands feel easier together. Sign in to discover and plan meetups.'}
          </p>
        </div>
        {initError && <p role="alert" className="mb-4 text-sm text-rose-300">{initError}</p>}
        <button
          type="button"
          onClick={() => setIsAuthModalOpen(true)}
          className="rounded-xl bg-emerald-500 px-5 py-3 font-bold text-slate-950"
        >
          {lang === 'pl' ? 'Zaloguj się lub utwórz konto' : 'Sign in or create an account'}
        </button>
        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
          lang={lang}
          onAuthSuccess={handleAuthSuccess}
          demoUsers={import.meta.env.DEV ? allUsers : []}
        />
      </div>
    );
  }

  if (ageBlocked) {
    const message = pilotAgeChallengeAvailable
      ? lang === 'pl'
        ? 'Wyjścia i odkrywanie osób są wstrzymane, dopóki operator nie potwierdzi na żywo, że masz co najmniej 18 lat. Sam kod SMS potwierdza tylko numer telefonu.'
        : lang === 'uk'
          ? 'Зустрічі та пошук людей недоступні, доки оператор особисто не підтвердить, що вам виповнилося 18 років. SMS підтверджує лише номер телефону.'
          : lang === 'ru'
            ? 'Встречи и поиск людей недоступны, пока оператор лично не подтвердит, что вам исполнилось 18 лет. SMS подтверждает только номер телефона.'
            : 'Outings and discovery are paused until a pilot operator checks in person that you are at least 18. SMS only confirms a phone number.'
      : lang === 'pl'
      ? 'Wyjścia i odkrywanie osób są wstrzymane. Pilot jest wyłącznie dla osób 18+, a zatwierdzona weryfikacja wieku nie jest jeszcze dostępna. Kod SMS potwierdza tylko numer telefonu.'
      : lang === 'uk'
        ? 'Зустрічі та пошук людей призупинено. Пілот доступний лише для осіб 18+, а перевірка віку ще недоступна. SMS підтверджує тільки номер телефону.'
        : lang === 'ru'
          ? 'Встречи и поиск людей приостановлены. Пилот доступен только совершеннолетним (18+), а проверка возраста пока недоступна. SMS подтверждает только номер телефона.'
          : 'Outings and people discovery are paused. This pilot is 18+ only, and approved age verification is not available yet. SMS confirms a phone number, not age.';
    return (
      <div className="min-h-dvh overflow-y-auto bg-[#0b0f19] flex items-start justify-center p-5 text-slate-100">
        <main className="max-w-md w-full rounded-3xl border border-amber-500/30 bg-slate-900 p-6 space-y-4 text-center">
          <h1 className="text-xl font-bold">CartMate · 18+</h1>
          <p role="status" className="text-sm leading-relaxed text-slate-300">{message}</p>
          {pilotAgeChallengeAvailable && (
            <div className="space-y-3 rounded-2xl border border-slate-700 p-4 text-left">
              <p className="text-xs text-slate-300">
                {lang === 'pl' ? 'Kod konta do okazania operatorowi: ' : 'Account code to show the pilot operator: '}
                <code className="rounded bg-slate-800 px-2 py-1 text-sky-200 select-all">{currentUser.id}</code>
              </p>
              <button type="button" onClick={() => { void handleCreateAgeChallenge(); }} className="w-full rounded-xl bg-sky-400 px-4 py-3 font-bold text-slate-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300">
                {lang === 'pl' ? 'Wygeneruj kod do sprawdzenia 18+' : 'Generate a 5-minute age-check code'}
              </button>
              {ageChallenge && (
                <p role="status" className="text-xs text-slate-200">
                  {lang === 'pl' ? 'Jednorazowy kod dla operatora: ' : 'One-use code for the operator: '}
                  <code className="break-all rounded bg-slate-800 px-2 py-1 font-bold text-sky-200 select-all">{ageChallenge.challenge}</code>
                  <span className="block pt-2 text-slate-400">
                    {lang === 'pl' ? 'Ważny do: ' : 'Valid until: '}
                    {new Date(ageChallenge.expires_at).toLocaleTimeString(lang === 'pl' ? 'pl-PL' : 'en-GB')}
                  </span>
                </p>
              )}
              {ageChallengeError && <p role="alert" className="text-xs text-rose-300">{ageChallengeError}</p>}
            </div>
          )}
          {canModerateAge && pilotAgeChallengeAvailable && <PilotAgeConsole lang={lang} />}
          <button type="button" onClick={() => { void loadInitialData(); }} className="w-full rounded-xl bg-slate-700 px-4 py-3 font-semibold">
            {lang === 'pl' ? 'Sprawdź ponownie' : 'Check again'}
          </button>
          <button type="button" onClick={() => { void handleLogout(); }} className="w-full rounded-xl border border-slate-600 px-4 py-3 font-semibold">
            {lang === 'pl' ? 'Wyloguj się' : 'Sign out'}
          </button>
        </main>
      </div>
    );
  }

  // Shell Layout Container
  return (
    <div className="h-dvh bg-[#070a13] flex items-center justify-center sm:p-4 text-slate-100 font-sans">
      <div
        className={`w-full bg-[#0b0f19] transition-all flex flex-col ${
          isMobileFrame
            ? 'max-w-[420px] h-[92dvh] sm:h-[min(840px,calc(100dvh-2rem))] rounded-3xl border border-slate-800 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)] overflow-hidden relative'
            : 'max-w-6xl h-dvh sm:h-[calc(100dvh-2rem)] border-x border-slate-800/80 shadow-2xl'
        }`}
      >
        {/* Mobile Speaker / Camera Notch if in Frame Mode */}
        {isMobileFrame && (
          <div className="h-6 bg-[#0f172a] flex items-center justify-center shrink-0 border-b border-slate-900/80">
            <div className="w-20 h-3.5 bg-slate-950 rounded-full flex items-center justify-center">
              <span className="w-2 h-2 rounded-full bg-slate-800" />
            </div>
          </div>
        )}

        {/* Persistent Top Header with Multi-Language (PL/EN/UK/RU), City & Auth Toggle */}
        <Header
          currentUser={currentUser}
          lang={lang}
          onSelectLanguage={(newLang: Language) => setLang(newLang)}
          isMobileFrame={isMobileFrame}
          onToggleMobileFrame={() => setIsMobileFrame(!isMobileFrame)}
          onNavigateSafety={() => setActiveTab('safety')}
          selectedCity={selectedCity}
          onSelectCity={handleSelectCity}
          onOpenAuth={() => setIsAuthModalOpen(true)}
        />

        {/* Scrollable Viewport Content */}
        <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
          <PrivacyBanner lang={lang} />
          {tripCancelledNotice && (
            <div role="status" className="mx-3 my-2 flex items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              <span>{translations[lang].tripCancelledNotice}</span>
              <button type="button" onClick={() => setTripCancelledNotice(false)} aria-label={translations[lang].dismissNotice} className="min-h-11 min-w-11 rounded-lg text-xl hover:bg-amber-500/10">×</button>
            </div>
          )}

          {/* Discovery Segmented Switcher (1:1 Outings, Micro-Pods 3-5, 10' Voice Calls) */}
          {['radar', 'pods', 'voice'].includes(activeTab) && (
            <div className="mx-4 my-2.5 flex items-center justify-center p-1 bg-slate-900/90 border border-slate-800 rounded-2xl max-w-md mx-auto shadow-sm">
              <button
                type="button"
                onClick={() => setActiveTab('radar')}
                aria-current={activeTab === 'radar' ? 'page' : undefined}
                className={`flex-1 py-2 px-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  activeTab === 'radar'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>{lang === 'pl' ? 'Wyjścia 1:1' : '1:1 Outings'}</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('pods')}
                aria-current={activeTab === 'pods' ? 'page' : undefined}
                className={`flex-1 py-2 px-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  activeTab === 'pods'
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{lang === 'pl' ? 'Pody 3-5' : 'Pods 3-5'}</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('voice')}
                aria-current={activeTab === 'voice' ? 'page' : undefined}
                className={`flex-1 py-2 px-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  activeTab === 'voice'
                    ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30 shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <PhoneCall className="w-3.5 h-3.5" />
                <span>{lang === 'pl' ? "Głos 10'" : "Voice 10'"}</span>
              </button>
            </div>
          )}
          {activeTab === 'pods' && (
            <PodFeed
              token={getStoredToken()}
              currentUserId={currentUser?.id}
              onRequireAuth={() => setIsAuthModalOpen(true)}
            />
          )}

          {activeTab === 'voice' && (
            <VoiceCallHUD
              token={getStoredToken()}
              currentUser={currentUser}
              lang={lang}
            />
          )}

          {activeTab === 'radar' && (
            <LiveRadarView
              currentUser={currentUser}
              pings={pings}
              cityName={selectedCity}
              lang={lang}
              onRefresh={loadInitialData}
              onJoinPing={handleJoinPing}
              onAcceptRequest={handleAcceptRequest}
              onViewTrip={() => setActiveTab('active_trip')}
              onOpenCreatePing={() => setShowCreateModal(true)}
            />
          )}

          {activeTab === 'new_ping' && (
            <div className="p-4">
              <CreatePingModal
                currentUser={currentUser}
                lang={lang}
                onClose={() => setActiveTab('radar')}
                onSubmit={handleCreatePing}
                onNavigateSafety={() => setActiveTab('safety')}
              />
            </div>
          )}

          {activeTab === 'safety' && (
            <SafetyHub
              currentUser={currentUser}
              lang={lang}
              onVerifyId={handleVerifyId}
              onToggleSafeHaven={handleToggleSafeHaven}
            />
          )}

          {activeTab === 'active_trip' && (
            <ActiveTripHUD
              currentUser={currentUser}
              trip={activeTrip}
              lang={lang}
              onCheckIn={handleCheckIn}
              onTriggerSos={handleTriggerSos}
              onCompleteTrip={handleCompleteTrip}
              onNavigateRadar={() => setActiveTab('radar')}
              onTripUpdated={(updated) => {
                if (updated.status === 'cancelled') {
                  setActiveTrip(null);
                  setTripCancelledNotice(true);
                } else {
                  setActiveTrip(updated);
                }
              }}
            />
          )}

          {activeTab === 'profile' && (
            <ProfileView
              currentUser={currentUser}
              allUsers={import.meta.env.DEV ? allUsers : []}
              stats={stats}
              lang={lang}
              onSwitchUser={handleSwitchUser}
              onNavigateSafety={() => setActiveTab('safety')}
              onOpenAuth={() => setIsAuthModalOpen(true)}
              onLogout={handleLogout}
              onUserUpdated={(u) => setCurrentUser(u)}
            />
          )}
        </main>

        {/* Floating / Center Ping Modal (when invoked from Header or Radar banner) */}
        {showCreateModal && activeTab !== 'new_ping' && (
          <CreatePingModal
            currentUser={currentUser}
            lang={lang}
            onClose={() => setShowCreateModal(false)}
            onSubmit={handleCreatePing}
            onNavigateSafety={() => {
              setShowCreateModal(false);
              setActiveTab('safety');
            }}
          />
        )}

        {/* Auth Modal (Login / Register / Switch) */}
        <AuthModal
          isOpen={isAuthModalOpen}
          onClose={() => setIsAuthModalOpen(false)}
          lang={lang}
          onAuthSuccess={handleAuthSuccess}
          demoUsers={import.meta.env.DEV ? allUsers : []}
        />

        {/* Persistent Bottom Mobile Nav */}
        <BottomNav
          activeTab={activeTab}
          lang={lang}
          hasNewChatActivity={hasNewChatActivity}
          onTabChange={(tab) => {
            if (tab === 'new_ping') {
              setShowCreateModal(true);
            } else {
              setActiveTab(tab);
            }
          }}
          activeTrip={activeTrip}
        />
      </div>
    </div>
  );
};

export default App;
