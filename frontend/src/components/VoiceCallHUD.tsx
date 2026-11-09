import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  PhoneCall,
  PhoneOff,
  Mic,
  MicOff,
  ShieldAlert,
  Clock,
  Sparkles,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import type { User, VoiceStatusResponse, VoiceCallPeer } from '../types';
import { fetchVoiceStatus, rateVoiceCall, hangupVoiceCall } from '../api';
import { realtime } from '../realtime/socket';

interface VoiceCallHUDProps {
  token: string | null;
  currentUser: User | null;
  lang?: string;
}

type CallState = 'idle' | 'searching' | 'connecting' | 'in_call' | 'ended';

export const VoiceCallHUD: React.FC<VoiceCallHUDProps> = ({ token, currentUser: _currentUser, lang = 'pl' }) => {
  const [statusData, setStatusData] = useState<VoiceStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [callState, setCallState] = useState<CallState>('idle');
  const [selectedTopic, setSelectedTopic] = useState<string>('Jak minął Ci dzisiejszy dzień?');
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [peerInfo, setPeerInfo] = useState<VoiceCallPeer | null>(null);
  const [_callRole, setCallRole] = useState<'offerer' | 'answerer' | null>(null);

  // Audio & WebRTC State
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(600);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [showBlockConfirm, setShowBlockConfirm] = useState<boolean>(false);

  // Rating State
  const [showRating, setShowRating] = useState<boolean>(false);
  const [lastCallId, setLastCallId] = useState<string | null>(null);
  const [selectedRating, setSelectedRating] = useState<'respectful' | 'neutral' | 'inappropriate'>('respectful');
  const [ratingDetails, setRatingDetails] = useState<string>('');
  const [ratingBlockPeer, setRatingBlockPeer] = useState<boolean>(false);
  const [ratingSubmitted, setRatingSubmitted] = useState<boolean>(false);

  // Refs
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);

  // Load Status
  const loadStatus = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await fetchVoiceStatus(token);
      setStatusData(data);
      if (data.icebreakers && data.icebreakers.length > 0 && !selectedTopic) {
        setSelectedTopic(data.icebreakers[0]);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Nie udało się pobrać statusu połączeń.');
    } finally {
      setLoading(false);
    }
  }, [token, selectedTopic]);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    loadStatus();
  }, [loadStatus]);

  // Cleanup WebRTC & Audio
  const cleanupMedia = useCallback(() => {
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
  }, []);

  useEffect(() => {
    return () => {
      cleanupMedia();
    };
  }, [cleanupMedia]);

  // Audio level analyser loop
  const startAudioAnalyser = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const checkVolume = () => {
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
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
      try {
        setCallState('connecting');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
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
          if (remoteAudioRef.current && event.streams[0]) {
            remoteAudioRef.current.srcObject = event.streams[0];
            remoteAudioRef.current.play().catch(() => {});
          }
        };

        pc.onicecandidate = (event) => {
          if (event.candidate) {
            realtime.send({
              action: 'voice.call_ice_candidate',
              call_id: callId,
              candidate: event.candidate,
            });
          }
        };

        pc.onconnectionstatechange = () => {
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
            if (callState === 'in_call' || callState === 'connecting') {
              handleCallEnded('connection_dropped');
            }
          }
        };

        if (role === 'offerer') {
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);
          realtime.send({
            action: 'voice.call_offer',
            call_id: callId,
            sdp: offer.sdp,
          });
        }
      } catch (err: any) {
        setErrorMsg('Błąd dostępu do mikrofonu: ' + (err.message || 'Wymagane uprawnienia'));
        setCallState('idle');
        cleanupMedia();
      }
    },
    [callState, cleanupMedia, handleCallEnded]
  );

  // WebSocket Event Listeners
  useEffect(() => {
    const unsubMatched = realtime.on('voice.call_matched', async (payload: any, env: any) => {
      const data = env?.call_id ? env : payload;
      if (!data || !data.call_id) return;

      setActiveCallId(data.call_id);
      setCallRole(data.role);
      setPeerInfo(data.peer);

      const iceServers = data.ice_servers || [];
      await initializeWebRtc(data.call_id, data.role, iceServers);
    });

    const unsubOffer = realtime.on('voice.call_offer', async (payload: any, env: any) => {
      const data = env?.sdp ? env : payload;
      const pc = peerConnectionRef.current;
      if (pc && data?.sdp) {
        try {
          await pc.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: data.sdp }));
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          realtime.send({
            action: 'voice.call_answer',
            call_id: data.call_id || activeCallId,
            sdp: answer.sdp,
          });
        } catch (e) {
          console.error('Error handling offer:', e);
        }
      }
    });

    const unsubAnswer = realtime.on('voice.call_answer', async (payload: any, env: any) => {
      const data = env?.sdp ? env : payload;
      const pc = peerConnectionRef.current;
      if (pc && data?.sdp) {
        try {
          await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: data.sdp }));
        } catch (e) {
          console.error('Error handling answer:', e);
        }
      }
    });

    const unsubIce = realtime.on('voice.call_ice_candidate', async (payload: any, env: any) => {
      const data = env?.candidate ? env : payload;
      const pc = peerConnectionRef.current;
      if (pc && data?.candidate) {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
        } catch (e) {
          console.error('Error adding ICE candidate:', e);
        }
      }
    });

    const unsubTimeout = realtime.on('voice.queue_timeout', (payload: any, env: any) => {
      const msg = env?.message || payload?.message || 'Brak dostępnych rozmówców w tej chwili.';
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
  }, [activeCallId, initializeWebRtc, handleCallEnded]);

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

  // Hangup Call
  const handleHangup = async (blockPeer = false) => {
    setShowBlockConfirm(false);
    if (activeCallId && token) {
      try {
        realtime.send({
          action: 'voice.call_hangup',
          call_id: activeCallId,
          reason: blockPeer ? 'user_blocked' : 'user_hangup',
          block_peer: blockPeer,
        });
        await hangupVoiceCall(activeCallId, token, blockPeer);
      } catch (e) {
        console.warn('Hangup REST error:', e);
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
      setErrorMsg('Nie udało się zapisać oceny: ' + (err.message || ''));
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
              {lang === 'pl' ? '10-Minutowe Rozmowy' : '10-Minute Voice'}
            </h1>
            <p className="text-xs text-slate-400">
              {lang === 'pl' ? 'Anonimowe, bezpieczne połączenia audio' : 'Ephemeral anonymous audio calls'}
            </p>
          </div>
        </div>

        <button
          onClick={loadStatus}
          disabled={loading}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition cursor-pointer"
          title="Odśwież"
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
              Szyfrowane audio • Bez nagrywania
            </span>
            <h2 className="text-2xl font-black text-white">
              {peerInfo ? `${peerInfo.first_name} (${peerInfo.city})` : 'Łączenie rozmówcy...'}
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto line-clamp-2">
              Temat: <span className="text-slate-200 font-semibold">{selectedTopic}</span>
            </p>
          </div>

          {/* Large Countdown Timer & Pulse Wave */}
          <div className="my-8 flex flex-col items-center justify-center relative">
            {/* Glowing audio activity ring */}
            <div
              className="absolute w-44 h-44 rounded-full border-2 border-indigo-500/20 transition-transform duration-75 ease-out"
              style={{
                transform: `scale(${1 + audioLevel / 180})`,
                borderColor: audioLevel > 15 ? 'rgba(99, 102, 241, 0.7)' : 'rgba(99, 102, 241, 0.2)',
                boxShadow:
                  audioLevel > 15
                    ? `0 0 ${audioLevel / 2}px rgba(99, 102, 241, 0.5)`
                    : 'none',
              }}
            />

            <div className="w-36 h-36 rounded-full bg-slate-900/90 border border-slate-800 flex flex-col items-center justify-center z-10 shadow-xl">
              <Clock
                className={`w-5 h-5 mb-1 ${
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
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                Limit 10:00
              </span>
            </div>
          </div>

          {/* Icebreaker Prompt Cards */}
          <div className="w-full bg-slate-900/60 border border-slate-800/80 rounded-2xl p-3.5 mb-6">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Pomysł na pytanie w ciszy:</span>
            </div>
            <p className="text-xs text-slate-300 italic leading-relaxed">
              "{selectedTopic}"
            </p>
          </div>

          {/* In-Call Controls */}
          <div className="w-full flex items-center justify-center gap-4">
            {/* Mute Button */}
            <button
              onClick={toggleMute}
              className={`flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition cursor-pointer ${
                isMuted
                  ? 'bg-amber-500/20 border border-amber-500/40 text-amber-400'
                  : 'bg-slate-800/90 border border-slate-700 text-slate-200 hover:text-white'
              }`}
              title={isMuted ? 'Wyłącz wyciszenie' : 'Wycisz mikrofon'}
            >
              {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
              <span className="text-[10px] mt-1 font-medium">{isMuted ? 'Mute' : 'Mic'}</span>
            </button>

            {/* Red Hangup Button */}
            <button
              onClick={() => handleHangup(false)}
              className="flex flex-col items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-rose-600 to-rose-500 text-white shadow-lg shadow-rose-600/30 hover:scale-105 transition cursor-pointer"
              title="Zakończ rozmowę"
            >
              <PhoneOff className="w-7 h-7" />
              <span className="text-[10px] mt-0.5 font-bold">Koniec</span>
            </button>

            {/* End & Block Button */}
            <button
              onClick={() => setShowBlockConfirm(true)}
              className="flex flex-col items-center justify-center w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 text-rose-400 hover:bg-rose-950/30 hover:border-rose-800 transition cursor-pointer"
              title="Zakończ i Zablokuj"
            >
              <ShieldAlert className="w-6 h-6" />
              <span className="text-[10px] mt-1 font-medium">Zablokuj</span>
            </button>
          </div>

          {/* Block Confirmation Dialog */}
          {showBlockConfirm && (
            <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 text-center">
                <ShieldAlert className="w-10 h-10 text-rose-400 mx-auto mb-3" />
                <h3 className="text-base font-bold text-white mb-2">Zakończyć i zablokować?</h3>
                <p className="text-xs text-slate-300 leading-relaxed mb-5">
                  Rozmowa zostanie natychmiast przerwana, a ten rozmówca nie będzie mógł połączyć się z Tobą ani pisać w żadnym kanale.
                </p>
                <div className="flex gap-2.5">
                  <button
                    onClick={() => setShowBlockConfirm(false)}
                    className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition"
                  >
                    Anuluj
                  </button>
                  <button
                    onClick={() => handleHangup(true)}
                    className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition shadow-lg shadow-rose-600/30"
                  >
                    Zablokuj teraz
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

          <h3 className="text-lg font-bold text-white mb-2">Szukamy rozmówcy...</h3>
          <p className="text-xs text-slate-400 max-w-xs mb-4">
            Dopasowujemy osobę z Twojego regionu na spokojną 10-minutową rozmowę.
          </p>

          <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-300 mb-8 max-w-xs">
            Temat: <span className="font-semibold text-indigo-300">{selectedTopic}</span>
          </div>

          <button
            onClick={handleLeaveQueue}
            className="px-6 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold transition cursor-pointer"
          >
            Anuluj wyszukiwanie
          </button>
        </div>
      )}

      {/* --- State 3: Lobby / Idle --- */}
      {callState === 'idle' && (
        <div className="flex-1 flex flex-col gap-5">
          {/* Schedule & Quota Widget */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400">Status okna rozmów</span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Otwarte (18:00 - 23:00)
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1 border-t border-slate-800/60">
              <div>
                <span className="text-[11px] text-slate-500 block">Dziś wykorzystano</span>
                <span className="text-sm font-bold text-slate-200">
                  {statusData ? `${statusData.daily_calls_used} / ${statusData.daily_limit}` : '0 / 3'}
                </span>
              </div>
              <div>
                <span className="text-[11px] text-slate-500 block">Przerwa po rozmowie</span>
                <span className="text-sm font-bold text-slate-200">
                  {statusData?.cooldown_remaining_seconds ? (
                    <span className="text-amber-400">{statusData.cooldown_remaining_seconds}s</span>
                  ) : (
                    'Brak (gotowy)'
                  )}
                </span>
              </div>
            </div>
          </div>

          {/* Privacy & Safe Rules Card */}
          <div className="bg-gradient-to-tr from-slate-900 to-indigo-950/40 border border-indigo-950/80 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold text-xs">
              <ShieldAlert className="w-4 h-4" />
              <span>Gwarancja bezpiecznej i życzliwej przestrzeni</span>
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              <li>Rozmowa trwa dokładnie 10 minut i kończy się automatycznie.</li>
              <li>Widoczne jest tylko Twoje imię i miasto (zero numerów telefonów).</li>
              <li>W każdej chwili masz 1-tap przycisk zakończenia i blokady.</li>
              <li>Połączenie jest bezpośrednie (P2P audio) bez zapisu na serwerze.</li>
            </ul>
          </div>

          {/* Topic Picker */}
          <div>
            <label className="text-xs font-bold text-slate-300 block mb-2">
              Wybierz temat przewodni rozmowy:
            </label>
            <div className="space-y-2">
              {(statusData?.icebreakers || [
                'Jak minął Ci dzisiejszy dzień?',
                'Twój ulubiony sprawdzony przepis na obiad?',
                'Ciekawy film, serial lub książka warta polecenia?',
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
                Boolean(statusData?.cooldown_remaining_seconds && statusData.cooldown_remaining_seconds > 0) ||
                Boolean(statusData?.daily_calls_used && statusData.daily_calls_used >= 3)
              }
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white font-bold text-sm shadow-xl shadow-indigo-600/25 flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PhoneCall className="w-5 h-5" />
              <span>
                {statusData?.cooldown_remaining_seconds && statusData.cooldown_remaining_seconds > 0
                  ? `Przerwa: ${statusData.cooldown_remaining_seconds}s`
                  : statusData?.daily_calls_used && statusData.daily_calls_used >= 3
                  ? 'Osiągnięto limit dzienny (3/3)'
                  : 'Połącz z kimś teraz (10 min)'}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* --- Post-Call Rating Modal --- */}
      {showRating && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 text-center">
            {ratingSubmitted ? (
              <div className="py-8">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                <h3 className="text-base font-bold text-white">Dziękujemy za ocenę!</h3>
                <p className="text-xs text-slate-400 mt-1">Pomagasz utrzymać życzliwą społeczność.</p>
              </div>
            ) : (
              <>
                <h3 className="text-base font-bold text-white mb-1">Jak przebiegła rozmowa?</h3>
                <p className="text-xs text-slate-400 mb-4">Twoja opinia jest w 100% anonimowa.</p>

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
                    <span className="text-[11px] font-bold">Miła</span>
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
                    <span className="text-[11px] font-bold">Neutralna</span>
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
                    <span className="text-[11px] font-bold">Nie na temat</span>
                  </button>
                </div>

                <textarea
                  value={ratingDetails}
                  onChange={(e) => setRatingDetails(e.target.value)}
                  placeholder="Dodatkowe uwagi (opcjonalnie)..."
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
                  <span>Zablokuj tego rozmówcę na przyszłość</span>
                </label>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowRating(false)}
                    className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-400 text-xs font-semibold hover:bg-slate-700 transition"
                  >
                    Pomiń
                  </button>
                  <button
                    onClick={handleSubmitRating}
                    className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition shadow-lg shadow-indigo-600/30"
                  >
                    Zapisz ocenę
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
