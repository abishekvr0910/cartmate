import React, { useState, useEffect } from 'react';
import { Flame, Users, Check, Plus, MapPin, Clock, Coins, Sparkles, X, MessageCircle, Send } from 'lucide-react';
import type { HotspotSpot, User, ChatMessage } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';
import { fetchHotspots, voteHotspot, unvoteHotspot, createHotspot, fetchOuting, joinOuting, leaveOuting, fetchChatRoom, sendChatMessage, reportUser } from '../api';
import { realtime } from '../realtime/socket';
import { UserAvatar } from './UserAvatar';
import { useDialogFocus } from '../hooks/useDialogFocus';

interface SpotVotingWidgetProps {
  currentUser: User;
  cityName?: string;
  lang: Language;
  onJoinCrew?: (spot: HotspotSpot) => void;
}

const INITIAL_SPOTS: HotspotSpot[] = [
  {
    id: 'spot_burgerking',
    name: 'Burger King Katowice Dworzec 24h',
    category: 'late_night',
    emoji: '🍔',
    address: 'Plac Szewczyka 2, Katowice',
    target_time: 'Dziś, 23:30',
    description: 'Nocne gastro po pracy/uczelni w Katowicach. Ktoś chętny dołączyć, pogadać i coś zjeść zamiast siedzieć samemu?',
    cost_policy: 'Każdy zamawia dla siebie lub dzielimy kupony 2w1',
    votes_count: 3,
    voter_avatars: [
      'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150',
      'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150',
      'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150',
    ],
    threshold: 3,
    group_formed: true,
  },
  {
    id: 'spot_biedronka',
    name: 'Biedronka Mariacka Katowice',
    category: 'grocery',
    emoji: '🛒',
    address: 'ul. Mariacka 2, Katowice',
    target_time: 'Dziś, 19:00',
    description: 'Promocja 2+2 gratis na nabiał, kawę i bakalie. Szukamy osób do rozdzielenia wielosztuk!',
    cost_policy: 'Podział paragonu 50/50 na miejscu przez BLIK',
    votes_count: 2,
    voter_avatars: [
      'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150',
      'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150',
    ],
    threshold: 3,
    group_formed: false,
  },
  {
    id: 'spot_cafe_nero',
    name: 'Kafej / Strefa Kultury',
    category: 'cafe',
    emoji: '☕',
    address: 'ul. Uniwersytecka 13, Katowice',
    target_time: 'Jutro, 14:00',
    description: 'Wspólny stolik na pracę z laptopem i luźną przerwę na kawę. Praca w kawiarni zamiast samotnego home office.',
    cost_policy: 'Każdy płaci za swoją kawę / zrzutka na ciasto',
    votes_count: 3,
    voter_avatars: [
      'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150',
      'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150',
    ],
    threshold: 3,
    group_formed: true,
  },
  {
    id: 'spot_ikea',
    name: 'IKEA Katowice (Wyjazd kombi)',
    category: 'home',
    emoji: '🛋️',
    address: 'Al. Roździeńskiego 95, Katowice',
    target_time: 'Sobota, 11:00',
    description: 'Jadę dużym kombi po regał Kallax i klopsiki. Mam 2 wolne miejsca w aucie!',
    cost_policy: 'Zrzutka na paliwo (15 zł) przez BLIK',
    votes_count: 2,
    voter_avatars: [
      'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150',
      'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150',
    ],
    threshold: 3,
    group_formed: false,
  },
];

const SpotVotingWidgetComponent: React.FC<SpotVotingWidgetProps> = ({
  currentUser,
  cityName = 'Katowice',
  lang,
  onJoinCrew,
}) => {
  const t = translations[lang];
  const [spots, setSpots] = useState<HotspotSpot[]>(import.meta.env.DEV ? INITIAL_SPOTS : []);
  const [userVotes, setUserVotes] = useState<Record<string, boolean>>({});
  const [activeCrewModalSpot, setActiveCrewModalSpot] = useState<HotspotSpot | null>(null);
  const [showSuggestModal, setShowSuggestModal] = useState(false);
  const [newSpotName, setNewSpotName] = useState('');
  const [newSpotAddress, setNewSpotAddress] = useState('');
  const [newSpotTime, setNewSpotTime] = useState('');
  const [newSpotNote, setNewSpotNote] = useState('');
  const [newSpotEmoji, setNewSpotEmoji] = useState('🍕');

  // Real-time Outing Chat state
  const [activeChatSpot, setActiveChatSpot] = useState<HotspotSpot | null>(null);
  const [chatRoomId, setChatRoomId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [newMsgText, setNewMsgText] = useState('');
  const [isSendingMsg, setIsSendingMsg] = useState(false);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);
  const [reportTarget, setReportTarget] = useState<ChatMessage | null>(null);
  const [reportDetails, setReportDetails] = useState('');
  const [reportCategory, setReportCategory] = useState('harassment');
  const [reportSubmitted, setReportSubmitted] = useState(false);

  useDialogFocus('spot-suggest-dialog', showSuggestModal, () => setShowSuggestModal(false));
  useDialogFocus('spot-join-dialog', !!activeCrewModalSpot, () => setActiveCrewModalSpot(null));
  useDialogFocus('spot-chat-dialog', !!activeChatSpot, () => {
    setActiveChatSpot(null);
    setChatRoomId(null);
  });

  // Real-time synchronization of hotspot votes and outings
  useEffect(() => {
    let active = true;
    const refresh = () => {
      void fetchHotspots(cityName)
        .then((visibleSpots) => {
          if (active) setSpots(visibleSpots);
        })
        .catch((error) => console.error('Could not refresh neighborhood spots:', error));
    };
    const unsubVote = realtime.on('hotspot.voted', refresh);
    const unsubOuting = realtime.on('outing.created', refresh);
    return () => {
      active = false;
      unsubVote();
      unsubOuting();
    };
  }, [cityName]);

  // Real-time chat messages listener
  useEffect(() => {
    if (!chatRoomId) return;
    const unsubChat = realtime.on('chat.message', (msg: ChatMessage) => {
      if (msg.chat_room_id === chatRoomId) {
        setChatMessages((prev) => {
          if (prev.some((m) => m.id === msg.id)) return prev;
          return [...prev, msg];
        });
      }
    });
    realtime.subscribe(`chat:${chatRoomId}`);
    return () => {
      unsubChat();
      realtime.unsubscribe(`chat:${chatRoomId}`);
    };
  }, [chatRoomId]);

  useEffect(() => {
    let isMounted = true;
    fetchHotspots(cityName)
      .then((data) => {
        if (!isMounted) return;
        setSpots(data);
        const votes: Record<string, boolean> = {};
        data.forEach((s) => {
          // Avatars are not identities: multiple accounts can share one (or
          // have an empty avatar). Only the authenticated server flag counts.
          if (s.user_voted) {
            votes[s.id] = true;
          }
        });
        setUserVotes(votes);
      })
      .catch((e) => console.error('Failed to load hotspots', e));

    return () => {
      isMounted = false;
    };
  }, [cityName, currentUser.id]);

  const handleOpenChat = async (spot: HotspotSpot) => {
    if (!spot.user_joined) return;
    setGroupError(null);
    setReportTarget(null);
    setReportSubmitted(false);
    setActiveCrewModalSpot(null);
    setActiveChatSpot(spot);
    setIsLoadingChat(true);
    try {
      if (spot.outing_id) {
        const outing = await fetchOuting(spot.outing_id);
        setChatRoomId(outing.chat_room_id);
        const room = await fetchChatRoom(outing.chat_room_id);
        setChatMessages(room.messages || []);
      }
    } catch (e) {
      setGroupError(e instanceof Error ? e.message : 'Could not load the group chat.');
      setActiveChatSpot(null);
    } finally {
      setIsLoadingChat(false);
    }
  };

  const handleJoinCrew = async (spot: HotspotSpot) => {
    if (!spot.outing_id) {
      alert(lang === 'pl' ? 'Ta ekipa nie jest jeszcze gotowa do dołączenia.' : 'This outing is not ready to join yet.');
      return;
    }
    try {
      await joinOuting(spot.outing_id);
      const joinedSpot = { ...spot, user_joined: true };
      setSpots((previous) => previous.map((item) => item.id === spot.id ? joinedSpot : item));
      onJoinCrew?.(spot);
      await handleOpenChat(joinedSpot);
    } catch (error: any) {
      setGroupError(error.message || 'Could not join this outing.');
    }
  };

  const handleLeaveCrew = async (spot: HotspotSpot) => {
    if (!spot.outing_id) return;
    try {
      await leaveOuting(spot.outing_id);
      setSpots((previous) => previous.map((item) => item.id === spot.id ? { ...item, user_joined: false } : item));
      setChatRoomId(null);
      // Keep the already loaded messages in this open window so a person who
      // left for safety can still cite one in a report. Server access is gone.
      setActiveChatSpot((current) => current?.id === spot.id ? { ...current, user_joined: false } : current);
      setActiveCrewModalSpot(null);
      setGroupError(null);
    } catch (error) {
      setGroupError(error instanceof Error ? error.message : 'Could not leave this outing.');
    }
  };

  const handleReportMessage = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!reportTarget || !activeChatSpot?.outing_id || !reportDetails.trim()) return;
    try {
      await reportUser(reportTarget.sender_id, reportCategory, reportDetails.trim(), undefined, reportTarget.id, activeChatSpot.outing_id);
      setReportSubmitted(true);
      setReportTarget(null);
      setReportDetails('');
      setGroupError(null);
    } catch (error) {
      setGroupError(error instanceof Error ? error.message : 'Could not submit the report.');
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsgText.trim() || !chatRoomId || isSendingMsg) return;
    setIsSendingMsg(true);
    try {
      const sent = await sendChatMessage(chatRoomId, newMsgText.trim());
      setChatMessages((prev) => {
        if (prev.some((m) => m.id === sent.id)) return prev;
        return [...prev, sent];
      });
      setNewMsgText('');
    } catch (e: any) {
      alert(e.message || 'Błąd wysyłania wiadomości');
    } finally {
      setIsSendingMsg(false);
    }
  };

  const handleToggleVote = async (spotId: string) => {
    const hasVoted = !!userVotes[spotId];
    setUserVotes((prev) => ({ ...prev, [spotId]: !hasVoted }));

    try {
      const updated = hasVoted ? await unvoteHotspot(spotId) : await voteHotspot(spotId);
      setSpots((prev) => prev.map((spot) => (spot.id === spotId ? updated : spot)));
    } catch (err: any) {
      setUserVotes((prev) => ({ ...prev, [spotId]: hasVoted }));
      alert(err.message || 'Błąd zapisu głosu');
    }
  };

  const handleAddCustomSpot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSpotName.trim()) return;

    try {
      const created = await createHotspot({
        city: cityName,
        name: newSpotName.trim(),
        category: 'late_night',
        emoji: newSpotEmoji,
        address: newSpotAddress.trim() || `${cityName} Centrum`,
        target_time: newSpotTime.trim() || 'Dziś wieczorem',
        description: newSpotNote.trim() || 'Szukamy chętnych do wspólnego wyjścia w to miejsce!',
        cost_policy: 'Każdy za siebie lub podział przez BLIK',
      });

      setSpots((prev) => [created, ...prev]);
      setUserVotes((prev) => ({ ...prev, [created.id]: true }));
      setShowSuggestModal(false);
      setNewSpotName('');
      setNewSpotAddress('');
      setNewSpotTime('');
      setNewSpotNote('');
    } catch (err: any) {
      alert(err.message || 'Błąd tworzenia spotu');
    }
  };

  return (
    <div className="rounded-3xl bg-gradient-to-b from-slate-900/90 via-slate-900 to-slate-950 p-4 border border-slate-800 shadow-xl space-y-4">
      {/* Header with Crowdsourced Voting Callout */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1 basis-40">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 shrink-0 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <Flame className="w-4 h-4 fill-rose-400" />
            </div>
            <h3 className="min-w-0 break-words text-sm font-extrabold text-white tracking-tight">
              {t.spotVotingTitle} ({cityName})
            </h3>
          </div>
          <p className="text-[11px] text-slate-400 mt-1 leading-snug">
            {t.spotVotingSub}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowSuggestModal(true)}
          className="min-h-10 max-w-full break-words text-[11px] font-bold text-amber-300 hover:text-amber-200 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 px-2.5 py-1 rounded-xl transition cursor-pointer"
        >
          {t.suggestSpotBtn}
        </button>
      </div>

      {groupError && <p role="alert" className="rounded-xl border border-rose-500/50 bg-rose-950/30 p-3 text-xs text-rose-200">{groupError}</p>}

      {/* Spot Voting Cards Grid */}
      <div className="space-y-3">
        {spots.length === 0 && (
          <p role="status" className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-center text-xs text-slate-400">
            {lang === 'pl'
              ? 'Nie ma teraz widocznych propozycji w tym mieście. Możesz dodać pierwszą.'
              : 'No proposals are currently visible in this city. You can add the first one.'}
          </p>
        )}
        {spots.map((spot) => {
          const votesNeeded = Math.max(0, spot.threshold - spot.votes_count);

          return (
            <div
              key={spot.id}
              className={`p-3.5 rounded-2xl border transition-all ${
                spot.group_formed
                  ? 'bg-gradient-to-r from-amber-950/20 via-slate-900 to-emerald-950/20 border-amber-500/40 shadow-md'
                  : 'bg-slate-900/80 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              {/* Top Row: Emoji, Name, Group Formed Badge */}
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex flex-1 basis-40 items-center gap-2.5 min-w-0">
                  <div className="text-2xl p-2 rounded-2xl bg-slate-800/70 border border-slate-700/60 shrink-0">
                    {spot.emoji}
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-bold text-white break-words">
                      {spot.name}
                    </h4>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                      <span className="flex items-center gap-0.5 truncate">
                        <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
                        {spot.address}
                      </span>
                      <span>•</span>
                      <span className="text-amber-300 font-semibold flex items-center gap-0.5 shrink-0">
                        <Clock className="w-3 h-3 text-amber-400" />
                        {spot.target_time}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Status Badge */}
                {spot.group_formed ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-gradient-to-r from-amber-500/20 to-emerald-500/20 text-amber-300 border border-amber-500/40 shrink-0 animate-pulse">
                    <span>🔥</span>
                    <span>{t.spotGroupFormed}</span>
                  </span>
                ) : (
                  <span className="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-full border border-slate-700/60 shrink-0">
                    {votesNeeded} {lang === 'pl' ? 'głosy do ekipy' : 'votes to form'}
                  </span>
                )}
              </div>

              {/* Description & Intention */}
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                {spot.description}
              </p>

              {/* Natural Cost / Splitting Policy Pill */}
              <div className="mt-2 flex max-w-full items-center gap-1.5 break-words text-[10px] text-teal-300 bg-teal-950/40 border border-teal-800/40 px-2.5 py-1 rounded-xl font-medium w-fit">
                <Coins className="w-3 h-3 text-teal-400" />
                <span>{spot.cost_policy}</span>
              </div>

              {/* Bottom Actions Row: Voters, Vote button, Join Crew button */}
              <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between gap-2 flex-wrap">
                {/* Voter Avatars */}
                <div className="flex items-center gap-1.5">
                  <div className="flex -space-x-2">
                    {spot.voter_avatars.slice(0, 4).map((avatar, idx) => (
                      <UserAvatar key={idx} name={lang === 'pl' ? 'Uczestnik' : 'Participant'} src={avatar} className="w-6 h-6 rounded-full border-2 border-slate-900 text-[8px]" />
                    ))}
                  </div>
                  <span className="text-[11px] font-bold text-slate-300">
                    {spot.votes_count} {lang === 'pl' ? 'chętnych sąsiadów' : 'interested'}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {/* Vote Toggle Button */}
                  <button
                    type="button"
                    onClick={() => handleToggleVote(spot.id)}
                    className={`min-h-10 px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1 cursor-pointer active:scale-95 ${
                      spot.user_voted
                        ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                    }`}
                  >
{spot.user_voted ? (
                      <>
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                        <span>{t.spotVotedBtn}</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5 stroke-[3]" />
                        <span>{t.spotVoteBtn}</span>
                      </>
                    )}
                  </button>

                  {/* Join Crew Button (when formed) */}
                  {spot.group_formed && (
                    <button
                      type="button"
                      onClick={() => {
                        setActiveCrewModalSpot(spot);
                      }}
                      className="min-h-10 px-3 py-1.5 rounded-xl text-xs font-extrabold bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-400 hover:to-amber-300 text-slate-950 flex items-center gap-1 shadow-md shadow-amber-500/25 cursor-pointer active:scale-95"
                    >
                      <Users className="w-3.5 h-3.5 text-slate-950" />
                      <span>{t.spotJoinCrew}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Suggest Spot Modal */}
      {showSuggestModal && (
        <div
          id="spot-suggest-dialog"
          className="app-dialog fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="suggest-spot-title"
          tabIndex={-1}
        >
          <div className="my-auto w-full max-w-sm max-h-[calc(100dvh-1.5rem)] overflow-y-auto rounded-3xl bg-slate-900 border border-slate-800 p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 id="suggest-spot-title" className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span>{t.suggestModalTitle}</span>
              </h3>
              <button
                onClick={() => setShowSuggestModal(false)}
                aria-label="Zamknij okno"
                className="flex min-h-10 min-w-10 items-center justify-center text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddCustomSpot} className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Emoji & Nazwa Miejsca
                </label>
                <div className="flex gap-2">
                  <select
                    aria-label={lang === 'pl' ? 'Symbol miejsca' : 'Place symbol'}
                    value={newSpotEmoji}
                    onChange={(e) => setNewSpotEmoji(e.target.value)}
                    className="p-2 rounded-xl bg-slate-800 border border-slate-700 text-base"
                  >
                    <option value="🍔">🍔</option>
                    <option value="☕">☕</option>
                    <option value="🛒">🛒</option>
                    <option value="🍕">🍕</option>
                    <option value="🍿">🍿</option>
                    <option value="🥦">🥦</option>
                    <option value="🛋️">🛋️</option>
                  </select>
                  <input
                    aria-label={lang === 'pl' ? 'Nazwa miejsca' : 'Place name'}
                    type="text"
                    required
                    placeholder="np. Kawiarnia Relaks, Lidl Tamka, Pizza..."
                    value={newSpotName}
                    onChange={(e) => setNewSpotName(e.target.value)}
                    className="flex-1 p-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Ulica / Okolica
                </label>
                <input
                  aria-label={lang === 'pl' ? 'Ulica lub okolica' : 'Street or area'}
                  type="text"
                    placeholder="np. ul. Mariacka 2, Katowice"
                  value={newSpotAddress}
                  onChange={(e) => setNewSpotAddress(e.target.value)}
                  className="w-full p-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Proponowana godzina
                </label>
                <input
                  aria-label={lang === 'pl' ? 'Proponowana godzina' : 'Proposed time'}
                  type="text"
                  placeholder="np. Dziś, 22:30 lub Jutro 14:00"
                  value={newSpotTime}
                  onChange={(e) => setNewSpotTime(e.target.value)}
                  className="w-full p-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Dlaczego warto? (Intencja)
                </label>
                <textarea
                  aria-label={lang === 'pl' ? 'Dlaczego warto' : 'Why this place'}
                  rows={2}
                  placeholder="np. Mają super pizzę w promocji i miłą atmosferę do rozmowy!"
                  value={newSpotNote}
                  onChange={(e) => setNewSpotNote(e.target.value)}
                  className="w-full p-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowSuggestModal(false)}
                  className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
                >
                  Anuluj
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold shadow-md shadow-amber-500/20"
                >
                  Opublikuj propozycję
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Crew Group Formed Modal / Confirmation */}
      {activeCrewModalSpot && (
        <div id="spot-join-dialog" role="dialog" aria-modal="true" aria-labelledby="spot-join-title" tabIndex={-1} className="app-dialog fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="my-auto w-full max-w-sm max-h-[calc(100dvh-1.5rem)] overflow-y-auto rounded-3xl bg-slate-900 border border-amber-500/40 p-5 shadow-2xl space-y-4 text-center">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center mx-auto text-3xl">
              {activeCrewModalSpot.emoji}
            </div>

            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded-full border border-amber-800/40">
                🔥 Ekipa gotowa
              </span>
              <h3 id="spot-join-title" className="text-base font-black text-white mt-1">
                {activeCrewModalSpot.name}
              </h3>
              <p className="text-xs text-slate-300 mt-1">
                Zbiórka: <span className="font-semibold text-amber-300">{activeCrewModalSpot.target_time}</span>
              </p>
            </div>

            <div className="p-3 rounded-2xl bg-slate-800/70 border border-slate-700 text-xs text-slate-300 space-y-1 text-left">
              <p className="font-semibold text-white flex items-center gap-1.5">
                <Coins className="w-3.5 h-3.5 text-teal-400" />
                <span>Zasady rozliczenia:</span>
              </p>
              <p className="text-[11px] text-slate-300 pl-5">
                {activeCrewModalSpot.cost_policy}
              </p>
            </div>

            <div className="flex items-center justify-center gap-2">
              <div className="flex -space-x-2">
                {activeCrewModalSpot.voter_avatars.map((avatar, idx) => (
                  <UserAvatar key={idx} name={lang === 'pl' ? 'Uczestnik' : 'Participant'} src={avatar} className="w-8 h-8 rounded-full border-2 border-slate-900 text-[10px]" />
                ))}
              </div>
              <span className="text-xs font-bold text-white">
                {activeCrewModalSpot.votes_count} {lang === 'pl' ? 'osób zainteresowanych (udział wymaga potwierdzenia)' : 'interested people (joining requires confirmation)'}
              </span>
            </div>

            <div className="pt-2 flex flex-col gap-2">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setActiveCrewModalSpot(null)}
                  className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
                >
                  Zamknij
                </button>
                {activeCrewModalSpot.user_joined && <button
                  type="button"
                  onClick={() => handleOpenChat(activeCrewModalSpot)}
                  className="flex-1 min-h-11 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 text-xs font-bold shadow-lg shadow-emerald-500/25 flex items-center justify-center gap-1.5"
                >
                  <MessageCircle className="w-3.5 h-3.5" />
                  <span>{lang === 'pl' ? 'Otwórz czat ekipy' : 'Open group chat'}</span>
                </button>}
              </div>
              {!activeCrewModalSpot.user_joined ? <button
                type="button"
                onClick={() => { void handleJoinCrew(activeCrewModalSpot); }}
                className="w-full min-h-11 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-400 text-slate-950 text-xs font-black shadow-lg shadow-amber-500/25"
              >
                {lang === 'pl' ? 'Potwierdź udział i otwórz czat' : 'Confirm joining and open chat'}
              </button> : <button
                type="button"
                onClick={() => { void handleLeaveCrew(activeCrewModalSpot); }}
                className="w-full min-h-11 rounded-xl border border-slate-600 bg-slate-800 text-slate-100 text-xs font-bold"
              >
                {lang === 'pl' ? 'Opuść ekipę bez kary' : 'Leave group without penalty'}
              </button>}
            </div>
          </div>
        </div>
      )}

      {/* Real-Time Outing Chat Modal */}
      {activeChatSpot && (
        <div
          id="spot-chat-dialog"
          className="app-dialog fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="outing-chat-title"
          tabIndex={-1}
        >
          <div className="w-full max-w-md h-[520px] max-h-[calc(100dvh-1.5rem)] rounded-3xl bg-slate-900 border border-slate-700 shadow-2xl flex flex-col overflow-hidden">
            {/* Chat Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center justify-center text-xl">
                  {activeChatSpot.emoji}
                </div>
                <div>
                  <h3 id="outing-chat-title" className="text-xs font-bold text-white leading-tight">
                    Czat ekipy: {activeChatSpot.name}
                  </h3>
                  <p className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>{lang === 'pl' ? 'Czat potwierdzonych uczestników' : 'Confirmed members chat'}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setActiveChatSpot(null);
                  setChatRoomId(null);
                }}
                aria-label="Zamknij czat"
                className="flex min-h-10 min-w-10 items-center justify-center text-slate-400 hover:text-white rounded-lg text-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Chat Messages List */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-950/30">
              {isLoadingChat ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-400">
                  Ładowanie wiadomości czatu...
                </div>
              ) : chatMessages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-2 text-slate-500 text-xs">
                  <MessageCircle className="w-8 h-8 text-slate-600" />
                  <p>Brak wiadomości w tym pokoju. Bądź pierwszym, który przywita ekipę!</p>
                </div>
              ) : (
                chatMessages.map((msg) => {
                  const isMe = msg.sender_id === currentUser.id;
                  const isSystem = msg.sender_id === 'system';

                  if (isSystem) {
                    return (
                      <div key={msg.id} className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 text-center">
                        {msg.text}
                      </div>
                    );
                  }

                  return (
                    <div
                      key={msg.id}
                      className={`flex items-start gap-2 ${isMe ? 'flex-row-reverse' : ''}`}
                    >
                      <UserAvatar name={msg.sender_name} src={msg.sender_avatar} className="w-7 h-7 rounded-full border border-slate-700 text-[10px]" />
                      <div
                        className={`max-w-[75%] p-2.5 rounded-2xl text-xs space-y-0.5 ${
                          isMe
                            ? 'bg-emerald-500 text-slate-950 font-medium rounded-tr-none'
                            : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 text-[10px] opacity-75">
                          <span className="font-bold">{msg.sender_name.split(' ')[0]}</span>
                        </div>
                        <p className="leading-snug break-words">{msg.text}</p>
                        {!isMe && <button
                          type="button"
                          onClick={() => { setReportTarget(msg); setReportSubmitted(false); }}
                          aria-label={lang === 'pl' ? `Zgłoś wiadomość użytkownika ${msg.sender_name}` : `Report message from ${msg.sender_name}`}
                          className="mt-1 min-h-10 rounded-lg border border-current px-2 text-[11px] font-semibold"
                        >
                          {lang === 'pl' ? 'Zgłoś' : 'Report'}
                        </button>}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {groupError && <p role="alert" className="mx-3 my-2 text-xs text-rose-300">{groupError}</p>}
            {reportSubmitted && <p role="status" className="mx-3 my-2 text-xs text-emerald-300">{lang === 'pl' ? 'Zgłoszenie zapisano do oceny przez człowieka. Kolejka nie jest monitorowana całodobowo.' : 'Report saved for human review. This queue is not monitored 24/7.'}</p>}
            {reportTarget && <form onSubmit={handleReportMessage} className="mx-3 mb-2 space-y-2 rounded-xl border border-amber-600/50 p-3 text-xs text-white">
              <p className="font-semibold">{lang === 'pl' ? `Zgłoś wiadomość od ${reportTarget.sender_name}` : `Report message from ${reportTarget.sender_name}`}</p>
              <label htmlFor="group-report-category" className="block">{lang === 'pl' ? 'Powód' : 'Reason'}</label>
              <select id="group-report-category" value={reportCategory} onChange={(event) => setReportCategory(event.target.value)} className="w-full rounded-lg bg-slate-800 p-2">
                <option value="harassment">{lang === 'pl' ? 'Nękanie' : 'Harassment'}</option>
                <option value="unsafe_behavior">{lang === 'pl' ? 'Niebezpieczne zachowanie' : 'Unsafe behavior'}</option>
                <option value="spam">Spam</option>
                <option value="other">{lang === 'pl' ? 'Inny powód' : 'Other'}</option>
              </select>
              <label htmlFor="group-report-details" className="block">{lang === 'pl' ? 'Co się wydarzyło?' : 'What happened?'}</label>
              <textarea id="group-report-details" required minLength={3} maxLength={2000} value={reportDetails} onChange={(event) => setReportDetails(event.target.value)} className="w-full rounded-lg bg-slate-800 p-2" rows={2} />
              <div className="flex gap-2">
                <button type="button" onClick={() => setReportTarget(null)} className="min-h-10 flex-1 rounded-lg border border-slate-600">{lang === 'pl' ? 'Wróć' : 'Back'}</button>
                <button type="submit" className="min-h-10 flex-1 rounded-lg bg-amber-500 text-slate-950 font-bold">{lang === 'pl' ? 'Wyślij zgłoszenie' : 'Submit report'}</button>
              </div>
              <p className="text-slate-400">{lang === 'pl' ? 'W nagłym zagrożeniu zadzwoń pod 112. CartMate nie monitoruje zgłoszeń na żywo.' : 'In immediate danger call 112. CartMate does not monitor reports live.'}</p>
            </form>}
            {activeChatSpot.user_joined ? <button type="button" onClick={() => { void handleLeaveCrew(activeChatSpot); }} className="mx-3 mb-2 min-h-11 rounded-xl border border-slate-700 text-xs text-slate-200">
              {lang === 'pl' ? 'Opuść ekipę bez kary' : 'Leave group without penalty'}
            </button> : <p role="status" className="mx-3 mb-2 text-xs text-slate-300">
              {lang === 'pl' ? 'Opuściłeś ekipę. Nie możesz już pisać; tę widoczną wiadomość nadal możesz zgłosić. Zamknięcie okna usunie ją z ekranu.' : 'You left the group. You can no longer send messages, but may report a message shown here. Closing this window clears it from view.'}
            </p>}

            {/* Chat Input */}
            {activeChatSpot.user_joined && <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-800 bg-slate-900 flex gap-2">
              <input
                aria-label={lang === 'pl' ? 'Wiadomość do ekipy' : 'Message to group'}
                type="text"
                value={newMsgText}
                onChange={(e) => setNewMsgText(e.target.value)}
                placeholder="Napisz do ekipy..."
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={!newMsgText.trim() || isSendingMsg}
                aria-label="Wyślij wiadomość"
                className="p-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition disabled:opacity-40 cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>}
          </div>
        </div>
      )}
    </div>
  );
};

export const SpotVotingWidget = React.memo(SpotVotingWidgetComponent);
