import React, { useState, useEffect, useCallback } from 'react';
import type { Pod, PodMessage } from '../types';
import { fetchPodFeed, joinPod, leavePod, fetchPodMessages, sendPodMessage } from '../api';
import { Users, MapPin, Clock, MessageSquare, CheckCircle2, AlertCircle, X, Send, Sparkles } from 'lucide-react';

interface PodFeedProps {
  token: string | null;
  currentUserId?: string | null;
  onRequireAuth?: () => void;
}

export const PodFeed: React.FC<PodFeedProps> = ({ token, currentUserId, onRequireAuth }) => {
  const [pods, setPods] = useState<Pod[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<string>('Wszystkie');
  
  // Chat drawer state
  const [activePodChat, setActivePodChat] = useState<Pod | null>(null);
  const [chatMessages, setChatMessages] = useState<PodMessage[]>([]);
  const [messageText, setMessageText] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

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

  const handleJoin = async (pod: Pod) => {
    if (!token) {
      onRequireAuth?.();
      return;
    }
    try {
      await joinPod(pod.id, token);
      await loadFeed();
    } catch (err: any) {
      alert(err.message || 'Błąd dołączania do poda');
    }
  };

  const handleLeave = async (pod: Pod) => {
    if (!token) return;
    try {
      await leavePod(pod.id, token);
      if (activePodChat?.id === pod.id) {
        setActivePodChat(null);
      }
      await loadFeed();
    } catch (err: any) {
      alert(err.message || 'Błąd opuszczania poda');
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
      setChatError(err.message || 'Czat jest zablokowany do momentu osiągnięcia quorum');
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

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-purple-800 text-white rounded-2xl p-6 mb-8 shadow-lg">
        <div className="flex items-center gap-2 text-blue-200 text-sm font-semibold mb-2">
          <Sparkles className="w-4 h-4" />
          <span>NOWOŚĆ: BEZPIECZNE WYJŚCIA W MAŁYCH GRUPACH</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mb-2">
          Micro-Pody (3–5 Osób)
        </h1>
        <p className="text-blue-100 text-sm sm:text-base max-w-2xl leading-relaxed">
          Zero presji i niezręczności spotkań 1-na-1 z nieznajomymi. Umawiaj się na wspólne spacery, naukę,
          planszówki i kawę w sprawdzonych miejscach publicznych. Czat odblokowuje się, gdy dołączą min. 3 osoby!
        </p>

        {/* City Filter Tabs */}
        <div className="flex flex-wrap gap-2 mt-5">
          {['Wszystkie', 'Katowice', 'Chorzów', 'Gliwice'].map((city) => (
            <button
              key={city}
              onClick={() => setSelectedCity(city)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition ${
                selectedCity === city
                  ? 'bg-white text-indigo-900 shadow'
                  : 'bg-indigo-900/60 text-white hover:bg-indigo-800'
              }`}
            >
              {city}
            </button>
          ))}
        </div>
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200 flex items-center gap-3 mb-6">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && pods.length === 0 && (
        <div className="bg-slate-50 border border-dashed border-slate-300 rounded-2xl p-10 text-center">
          <Users className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-700 mb-1">Brak aktywnych podów w tej okolicy</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Wkrótce pojawią się zaplanowane wyjścia grupowe w sprawdzonych lokalizacjach.
          </p>
        </div>
      )}

      {/* Pods Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {pods.map((pod) => {
          const isAtQuorum = pod.status === 'quorum' || pod.status === 'completed';
          const isJoined = pod.is_member || pod.members.some((m) => m.user_id === currentUserId);

          return (
            <div
              key={pod.id}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between"
            >
              <div>
                {/* Template & Status Header */}
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <span className="inline-block px-2.5 py-1 rounded-md text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100 mb-1.5">
                      {pod.template_name || pod.template_code} · {pod.template_duration_min} min
                    </span>
                    <h2 className="text-base font-bold text-slate-900 leading-snug">
                      {pod.title || pod.template_name}
                    </h2>
                  </div>

                  {isAtQuorum ? (
                    <span className="flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 flex-shrink-0">
                      <CheckCircle2 className="w-3 h-3" />
                      Quorum!
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 flex-shrink-0">
                      <Clock className="w-3 h-3" />
                      Formowanie
                    </span>
                  )}
                </div>

                {/* Third Place Venue & Meeting Point */}
                <div className="space-y-1.5 text-xs text-slate-600 mb-4 bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="flex items-center gap-2 font-semibold text-slate-800">
                    <MapPin className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
                    <span>{pod.place_name} ({pod.place_city})</span>
                  </div>
                  <div className="pl-5 text-slate-500">
                    Punkt zbiórki: <span className="text-slate-700 font-medium">{pod.place_meeting_point}</span>
                  </div>
                  <div className="pl-5 text-slate-500">
                    Kiedy: <span className="text-slate-700 font-medium">{formatDate(pod.starts_at)}, {formatTime(pod.starts_at)} - {formatTime(pod.ends_at)}</span>
                  </div>
                  <div className="pl-5 text-slate-500">
                    Wydatki: <span className="text-emerald-700 font-medium">
                      {pod.spend_expectation === 'no_expected_spend' ? 'Bezpłatnie (brak wydatków)' : 'Każdy płaci za siebie'}
                    </span>
                  </div>
                </div>

                {/* Seat Indicator & Quorum Progress */}
                <div className="mb-4">
                  <div className="flex justify-between items-center text-xs font-semibold mb-1.5">
                    <span className="flex items-center gap-1.5 text-slate-700">
                      <Users className="w-3.5 h-3.5 text-indigo-600" />
                      Miejsca: {pod.confirmed_count} / {pod.max_participants}
                    </span>
                    <span className="text-slate-500 text-[11px]">
                      {pod.spots_left > 0 ? `Wolne: ${pod.spots_left}` : 'Pełny pod'}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        isAtQuorum ? 'bg-emerald-500' : 'bg-indigo-600'
                      }`}
                      style={{ width: `${(pod.confirmed_count / pod.max_participants) * 100}%` }}
                    />
                  </div>
                  
                  {!isAtQuorum && (
                    <div className="text-[11px] text-amber-700 font-medium mt-1">
                      Potrzeba jeszcze min. {Math.max(0, pod.min_participants - pod.confirmed_count)} osoby do quorum
                    </div>
                  )}
                </div>

                {/* Member Avatars */}
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-[11px] text-slate-500 font-medium">Uczestnicy:</span>
                  <div className="flex -space-x-1.5 overflow-hidden">
                    {pod.members.map((m, idx) => (
                      <div
                        key={m.user_id || idx}
                        title={m.name}
                        className="inline-block h-6 w-6 rounded-full ring-2 ring-white bg-indigo-200 text-indigo-800 text-[10px] font-bold flex items-center justify-center uppercase"
                      >
                        {m.name ? m.name.charAt(0) : 'U'}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-100 flex gap-2">
                {isJoined ? (
                  <>
                    <button
                      onClick={() => handleLeave(pod)}
                      className="flex-1 py-2 px-3 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold transition"
                    >
                      Opuść
                    </button>
                    {isAtQuorum && (
                      <button
                        onClick={() => openChat(pod)}
                        className="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition shadow-sm"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        Czat grupy
                      </button>
                    )}
                  </>
                ) : (
                  <button
                    disabled={pod.spots_left <= 0}
                    onClick={() => handleJoin(pod)}
                    className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shadow-sm"
                  >
                    <Users className="w-4 h-4" />
                    {pod.spots_left > 0 ? 'Dołącz do poda' : 'Brak wolnych miejsc'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Group Chat Drawer Modal */}
      {activePodChat && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col justify-between">
            {/* Chat Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <div className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Quorum aktywne
                </div>
                <h3 className="text-sm font-bold text-slate-900 truncate">
                  {activePodChat.title || activePodChat.template_name}
                </h3>
                <p className="text-[11px] text-slate-500">
                  {activePodChat.place_name} · {activePodChat.confirmed_count} uczestników
                </p>
              </div>
              <button
                onClick={() => setActivePodChat(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {chatError && (
                <div className="p-3 bg-amber-50 text-amber-800 rounded-xl text-xs border border-amber-200 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{chatError}</span>
                </div>
              )}

              {chatMessages.length === 0 && !chatError && (
                <div className="text-center py-10 text-xs text-slate-400">
                  Brak wcześniejszych wiadomości. Przywitaj się z grupą!
                </div>
              )}

              {chatMessages.map((msg) => {
                const isMe = msg.sender_user_id === currentUserId;
                return (
                  <div key={msg.id} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                    <span className="text-[10px] text-slate-400 mb-0.5 px-1 font-medium">
                      {isMe ? 'Ty' : msg.sender_name} · {formatTime(msg.created_at)}
                    </span>
                    <div
                      className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed ${
                        isMe
                          ? 'bg-indigo-600 text-white rounded-br-sm'
                          : 'bg-slate-100 text-slate-800 rounded-bl-sm'
                      }`}
                    >
                      {msg.body}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-200 bg-slate-50 flex gap-2">
              <input
                type="text"
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                placeholder="Napisz do grupy..."
                className="flex-1 px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={sendingMsg || !messageText.trim()}
                className="p-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-xl transition flex items-center justify-center"
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
