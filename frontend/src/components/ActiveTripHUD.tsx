import React, { useEffect, useState } from 'react';
import { UserAvatar } from './UserAvatar';
import {
  MapPin,
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
  Send,
  ShoppingBag,
  KeyRound,
  Receipt,
  Plus,
  Copy,
  Check,
  Flame,
  Clock,
  ShieldCheck,
  UserX,
  Flag,
  Calendar,
  HeartHandshake,
  XCircle,
} from 'lucide-react';
import type { ChatMessage, Trip, User, ReportCategory } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';
import {
  verifyTripPin,
  addSplitItem,
  reviewTrip,
  acceptPlan,
  cancelTrip,
  updateTripPlan,
  submitTripFollowUp,
  blockUser,
  reportUser,
  fetchChatRoom,
  fetchTrip,
  sendChatMessage,
} from '../api';
import { realtime } from '../realtime/socket';
import { useDialogFocus } from '../hooks/useDialogFocus';

interface ActiveTripHUDProps {
  currentUser: User;
  trip: Trip | null;
  lang: Language;
  onCheckIn: (tripId: string) => Promise<void>;
  onTriggerSos: (tripId: string) => Promise<void>;
  onCompleteTrip: (tripId: string) => Promise<void>;
  onNavigateRadar: () => void;
  onTripUpdated: (updatedTrip: Trip) => void;
}

export const ActiveTripHUD: React.FC<ActiveTripHUDProps> = ({
  currentUser,
  trip,
  lang,
  onCheckIn,
  onTriggerSos,
  onCompleteTrip,
  onNavigateRadar,
  onTripUpdated,
}) => {
  const t = translations[lang];

  const [messages, setMessages] = useState<Array<{ id?: string; sender: string; text: string; time: string }>>([]);
  const [newMessage, setNewMessage] = useState('');
  const [chatError, setChatError] = useState<string | null>(null);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [showSosModal, setShowSosModal] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Handshake PIN state
  const [enteredPin, setEnteredPin] = useState('');
  const [pinError, setPinError] = useState<string | null>(null);

  // Splitter Modal state
  const [showAddSplitModal, setShowAddSplitModal] = useState(false);
  const [splitItemName, setSplitItemName] = useState('');
  const [splitItemPrice, setSplitItemPrice] = useState('');
  const [copiedBlik, setCopiedBlik] = useState(false);

  // Plan Acceptance & Low-Guilt Cancellation
  const [isAcceptingPlan, setIsAcceptingPlan] = useState(false);
  const [isSavingPlan, setIsSavingPlan] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [planDraft, setPlanDraft] = useState({
    what: '',
    when: '',
    meeting_point: '',
    estimated_duration_minutes: 45,
    cost_policy: 'buyer_pays_own',
    estimated_cost_pln: 0,
  });
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('changed_mind');
  const [cancelNote, setCancelNote] = useState('');
  const [isCancelling, setIsCancelling] = useState(false);

  // Private mutual meet-again choice
  const [wouldMeetAgain, setWouldMeetAgain] = useState<boolean | null>(null);
  const [followUpVibeTags, setFollowUpVibeTags] = useState<string[]>([]);
  const [followUpFeedback, setFollowUpFeedback] = useState('');
  const [isCompletingTrip, setIsCompletingTrip] = useState(false);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);

  // Report & Block Modals
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportCategory, setReportCategory] = useState<ReportCategory>('harassment');
  const [reportDetails, setReportDetails] = useState('');
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);
  const [reportSuccessMessage, setReportSuccessMessage] = useState<string | null>(null);

  const [showBlockModal, setShowBlockModal] = useState(false);
  const [blockReason, setBlockReason] = useState('');
  const [isBlocking, setIsBlocking] = useState(false);

  // Post-Trip Manner Review state
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewRating, setReviewRating] = useState(0);
  const [selectedBadges, setSelectedBadges] = useState<string[]>([]);
  const [reviewComment, setReviewComment] = useState('');

  // Truthful SOS state
  const [sosConsentChecked, setSosConsentChecked] = useState(false);
  const [isSosDispatching, setIsSosDispatching] = useState(false);
  const [sosError, setSosError] = useState<string | null>(null);

  useDialogFocus('trip-split-dialog', showAddSplitModal, () => setShowAddSplitModal(false));
  useDialogFocus('trip-sos-dialog', showSosModal, () => setShowSosModal(false));
  useDialogFocus('trip-review-dialog', showReviewModal, () => setShowReviewModal(false));
  useDialogFocus('trip-cancel-dialog', showCancelModal, () => setShowCancelModal(false));
  useDialogFocus('trip-report-dialog', showReportModal, () => setShowReportModal(false));
  useDialogFocus('trip-block-dialog', showBlockModal, () => setShowBlockModal(false));

  const activeTrip = trip;

  useEffect(() => {
    const roomId = activeTrip?.chat_room_id;
    if (!roomId) {
      return;
    }
    let cancelled = false;
    const toDisplayMessage = (message: ChatMessage) => ({
      id: message.id,
      sender: message.sender_id === currentUser.id ? (lang === 'pl' ? 'Ty' : 'You') : message.sender_name,
      text: message.text,
      time: new Date(message.created_at).toLocaleTimeString(lang === 'pl' ? 'pl-PL' : 'en-GB', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    });
    const onChatMessage = (message: ChatMessage) => {
      if (message.chat_room_id !== roomId) return;
      const next = toDisplayMessage(message);
      setMessages((prev) => prev.some((item) => item.id === next.id) ? prev : [...prev, next]);
    };
    const syncChatHistory = () => {
      void fetchChatRoom(roomId)
        .then((room) => {
          if (!cancelled) {
            setMessages((prev) => {
              const loaded = room.messages.map(toDisplayMessage);
              const loadedIds = new Set(loaded.map((message) => message.id));
              return [...loaded, ...prev.filter((message) => !message.id || !loadedIds.has(message.id))];
            });
          }
        })
        .catch((error: Error) => {
          if (!cancelled) setChatError(error.message || 'Could not load chat.');
        });
    };

    const unsubscribe = realtime.on<ChatMessage>('chat.message', onChatMessage);
    const unsubStatus = realtime.onStatusChange((status) => {
      if (status === 'connected') {
        syncChatHistory();
      }
    });
    const unsubReady = realtime.on('connection.ready', () => {
      syncChatHistory();
    });

    // Reset the visible thread when switching to another authorized room.
    // oxlint-disable-next-line react/set-state-in-effect
    setMessages([]);
    setChatError(null);
    syncChatHistory();

    return () => {
      cancelled = true;
      unsubscribe();
      unsubStatus();
      unsubReady();
    };
  }, [activeTrip?.chat_room_id, currentUser.id, lang]);

  const activeTripId = activeTrip?.id;
  useEffect(() => {
    // A retry on the same trip must not submit a successful review twice.
    // oxlint-disable-next-line react/set-state-in-effect
    setReviewSubmitted(false);
  }, [activeTripId]);
  const activePlanVersion = activeTrip?.plan_version;
  const destinationName = activeTrip?.destination_name || '';
  const rendezvousSpot = activeTrip?.rendezvous_spot || '';
  const planDetails = activeTrip?.plan_details;
  const canRecordEqualSplit = Boolean(
    activeTrip?.status === 'in_progress'
    && activeTrip.rendezvous_verified
    && activeTrip.host_accepted
    && activeTrip.companion_accepted
    && activeTrip.plan_details?.cost_policy === 'split_strictly_50_50'
  );
  useEffect(() => {
    if (!activeTripId) return;
    const details = planDetails;
    const allowedPolicies = new Set([
      'split_strictly_50_50', 'buyer_pays_own', 'host_treats',
      'companion_treats', 'no_purchase_browse_only', 'no_expected_spend',
    ]);
    const when = details?.when || '';
    // Sync the editable proposal whenever the server returns a new plan version.
    // oxlint-disable-next-line react/set-state-in-effect
    setPlanDraft({
      what: details?.what || `Outing together at ${destinationName}`,
      when: when.toLowerCase().startsWith('to be agreed') || when.toLowerCase() === 'do uzgodnienia' ? '' : when,
      meeting_point: details?.meeting_point || rendezvousSpot,
      estimated_duration_minutes: details?.estimated_duration_minutes || 45,
      cost_policy: details?.cost_policy && allowedPolicies.has(details.cost_policy) ? details.cost_policy : 'buyer_pays_own',
      estimated_cost_pln: details?.estimated_cost_pln || 0,
    });
  }, [activeTripId, activePlanVersion, destinationName, rendezvousSpot, planDetails]);

  if (!activeTrip) {
    return (
      <div className="p-6 text-center space-y-4 max-w-lg mx-auto py-20">
        <div className="w-16 h-16 rounded-3xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-600">
          <ShoppingBag className="w-8 h-8" />
        </div>
        <div className="space-y-1">
          <h2 className="text-base font-bold text-white">{t.noActiveTripTitle}</h2>
          <p className="text-xs text-slate-400">
            {t.noActiveTripDesc}
          </p>
        </div>
        <button
          onClick={onNavigateRadar}
          className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-emerald-500/20 cursor-pointer transition"
        >
          {t.exploreRadarBtn}
        </button>
      </div>
    );
  }

  const isHost = activeTrip.host.id === currentUser.id;
  const companion = isHost ? activeTrip.companion : activeTrip.host;
  const settlement = activeTrip.settlement;
  const settlementCreditor = settlement?.creditor_id === activeTrip.host.id
    ? activeTrip.host
    : settlement?.creditor_id === activeTrip.companion.id
      ? activeTrip.companion
      : null;
  const settlementDebtor = settlement?.debtor_id === activeTrip.host.id
    ? activeTrip.host
    : settlement?.debtor_id === activeTrip.companion.id
      ? activeTrip.companion
      : null;
  const userCheckedIn = isHost ? activeTrip.host_checked_in : activeTrip.companion_checked_in;
  const isPinVerified = activeTrip.rendezvous_verified;

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeTrip.chat_room_id || isSendingChat) return;
    setIsSendingChat(true);
    setChatError(null);
    try {
      const message = await sendChatMessage(activeTrip.chat_room_id, newMessage.trim());
      setMessages((prev) => prev.some((item) => item.id === message.id) ? prev : [...prev, {
        id: message.id,
        sender: lang === 'pl' ? 'Ty' : 'You',
        text: message.text,
        time: new Date(message.created_at).toLocaleTimeString(lang === 'pl' ? 'pl-PL' : 'en-GB', {
          hour: '2-digit',
          minute: '2-digit',
        }),
      }]);
      setNewMessage('');
    } catch (error: any) {
      setChatError(error.message || 'Could not send message.');
    } finally {
      setIsSendingChat(false);
    }
  };

  const isBothAccepted = Boolean(activeTrip.host_accepted && activeTrip.companion_accepted);

  const handleSavePlan = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSavingPlan(true);
    setPlanError(null);
    try {
      const updated = await updateTripPlan(activeTrip.id, planDraft);
      onTripUpdated(updated);
    } catch (error: any) {
      setPlanError(error.message || 'Could not save the plan.');
    } finally {
      setIsSavingPlan(false);
    }
  };

  const getCostPolicyLabel = (policy?: string) => {
    switch (policy) {
      case 'split_strictly_50_50':
        return lang === 'pl' ? 'Podział rachunku 50/50' : 'Split 50/50';
      case 'buyer_pays_own':
        return lang === 'pl' ? 'Każdy płaci za swoje' : 'Pay own items';
      case 'host_treats':
        return lang === 'pl' ? 'Gospodarz stawia' : 'Host treats';
      case 'companion_treats':
        return lang === 'pl' ? 'Towarzysz stawia' : 'Companion treats';
      case 'no_purchase_browse_only':
        return lang === 'pl' ? 'Tylko towarzyszenie (bez zakupów)' : 'Browse only (no purchase)';
      case 'no_expected_spend':
        return t.noExpectedSpend;
      default:
        return policy || (lang === 'pl' ? 'Podział 50/50' : 'Split 50/50');
    }
  };

  const handleAcceptPlanClick = async () => {
    try {
      setIsAcceptingPlan(true);
      const updated = await acceptPlan(activeTrip.id, activeTrip.plan_version);
      onTripUpdated(updated);
    } catch (err: any) {
      alert(err.message || 'Błąd akceptacji planu wyjścia');
    } finally {
      setIsAcceptingPlan(false);
    }
  };

  const handleConfirmCancelTrip = async () => {
    try {
      setIsCancelling(true);
      const cancelled = await cancelTrip(activeTrip.id, cancelReason, cancelNote);
      onTripUpdated(cancelled);
      setShowCancelModal(false);
      onNavigateRadar();
    } catch (err: any) {
      alert(err.message || 'Błąd anulowania wyjścia');
    } finally {
      setIsCancelling(false);
    }
  };

  const handleConfirmReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportDetails.trim()) return;
    try {
      setIsSubmittingReport(true);
      await reportUser(companion.id, reportCategory, reportDetails.trim(), activeTrip.id);
      setReportSuccessMessage(
        lang === 'pl'
          ? 'Zgłoszenie zapisano w kolejce. W razie bezpośredniego zagrożenia zadzwoń pod 112.'
          : 'Report saved in the review queue. If you are in immediate danger, call 112.'
      );
      setTimeout(() => {
        setShowReportModal(false);
        setReportSuccessMessage(null);
        setReportDetails('');
      }, 1800);
    } catch (err: any) {
      alert(err.message || 'Błąd wysyłania zgłoszenia');
    } finally {
      setIsSubmittingReport(false);
    }
  };

  const handleConfirmBlock = async () => {
    try {
      setIsBlocking(true);
      await blockUser(companion.id, blockReason || 'Blokada z poziomu aktywnego wyjścia');
      setShowBlockModal(false);
      alert(
        lang === 'pl'
          ? `Użytkownik ${companion.name} został zablokowany. Od tej pory jesteście dla siebie niewidoczni na radarze.`
          : `User ${companion.name} has been blocked. You will no longer see each other on radar.`
      );
      onNavigateRadar();
    } catch (err: any) {
      alert(err.message || 'Błąd blokowania użytkownika');
    } finally {
      setIsBlocking(false);
    }
  };

  const handleCheckInClick = async () => {
    if (!isBothAccepted) {
      alert(
        lang === 'pl'
          ? 'Obie strony muszą najpierw zaakceptować plan wyjścia przed potwierdzeniem obecności!'
          : 'Both participants must accept the plan terms before check-in!'
      );
      return;
    }
    setIsProcessing(true);
    try {
      await onCheckIn(activeTrip.id);
    } catch (e: any) {
      alert(e.message || 'Błąd potwierdzenia obecności');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleVerifyPinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPinError(null);
    if (!enteredPin.trim()) return;

    if (!isBothAccepted) {
      setPinError(
        lang === 'pl'
          ? 'Obie strony muszą najpierw zaakceptować plan wyjścia!'
          : 'Both participants must accept the plan first!'
      );
      return;
    }

    try {
      setIsProcessing(true);
      const updated = await verifyTripPin(activeTrip.id, enteredPin.trim());
      onTripUpdated(updated);
      setEnteredPin('');
    } catch (err: any) {
      setPinError(err.message || 'Błąd weryfikacji kodu PIN');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleAddSplitItem = async (e: React.FormEvent) => {
    e.preventDefault();
    const price = parseFloat(splitItemPrice.replace(',', '.'));
    if (!splitItemName.trim() || isNaN(price) || price <= 0) return;

    try {
      setIsProcessing(true);
      const updated = await addSplitItem(activeTrip.id, splitItemName.trim(), price, currentUser.id);
      onTripUpdated(updated);
      setSplitItemName('');
      setSplitItemPrice('');
      setShowAddSplitModal(false);
    } catch (err: any) {
      alert(err.message || 'Błąd dodawania produktu');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCopyBlik = async () => {
    if (settlement?.debtor_id !== currentUser.id || !settlementCreditor || settlement.amount_pln <= 0) return;
    try {
      // Never copy a potentially stale phone from a shared WebSocket event or
      // cached trip. REST rechecks acceptance and any newly added block.
      const latest = await fetchTrip(activeTrip.id);
      const latestSettlement = latest.settlement;
      const phone = latestSettlement?.debtor_id === currentUser.id
        ? (latestSettlement.creditor_id === latest.host.id ? latest.host.phone : latest.companion.phone)
        : null;
      if (!phone) {
        alert(lang === 'pl'
          ? 'Numer kontaktowy jest niedostępny. Sprawdź, czy plan został zaakceptowany i czy nie ma blokady.'
          : 'The contact number is unavailable. Check plan acceptance and blocking status.');
        return;
      }
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(phone);
      onTripUpdated(latest);
      setCopiedBlik(true);
      setTimeout(() => setCopiedBlik(false), 2500);
    } catch {
      alert(lang === 'pl' ? 'Nie udało się skopiować numeru.' : 'Could not copy the contact number.');
    }
  };

  const handleToggleBadge = (badge: string) => {
    if (selectedBadges.includes(badge)) {
      setSelectedBadges(selectedBadges.filter((b) => b !== badge));
    } else {
      setSelectedBadges([...selectedBadges, badge]);
    }
  };

  const handleSosClick = async () => {
    if (!sosConsentChecked) {
      setSosError(lang === 'pl' ? 'Potwierdź przed otwarciem opcji pomocy.' : 'Confirm before opening help options.');
      return;
    }
    setIsSosDispatching(true);
    setSosError(null);
    try {
      await onTriggerSos(activeTrip.id);
      setShowSosModal(false);
      setSosConsentChecked(false);
    } catch (e: any) {
      setSosError(e.message || (lang === 'pl' ? 'Nie udało się otworzyć opcji pomocy.' : 'Could not open help options.'));
    } finally {
      setIsSosDispatching(false);
    }
  };

  const handleFinishOuting = async () => {
    setReviewRating(0);
    setSelectedBadges([]);
    setReviewComment('');
    setWouldMeetAgain(null);
    setFollowUpVibeTags([]);
    setFollowUpFeedback('');
    setShowReviewModal(true);
  };

  const saveOptionalFollowUp = async () => {
    if (wouldMeetAgain === null) return;
    try {
      const result = await submitTripFollowUp(
        activeTrip.id,
        wouldMeetAgain,
        followUpVibeTags,
        followUpFeedback
      );
      if (result.is_mutual_buddy) {
        alert(t.mutualConfirmed);
      }
    } catch (error: any) {
      alert(error.message || t.followUpSaveFailed);
    }
  };

  const handleSubmitReview = async () => {
    try {
      setIsCompletingTrip(true);
      if (!reviewSubmitted) {
        await reviewTrip(activeTrip.id, reviewRating, selectedBadges, reviewComment);
        setReviewSubmitted(true);
      }
      await onCompleteTrip(activeTrip.id);
      await saveOptionalFollowUp();
      setShowReviewModal(false);
      onNavigateRadar();
    } catch (e: any) {
      alert(e.message || 'Błąd zapisu oceny');
    } finally {
      setIsCompletingTrip(false);
    }
  };

  const handleCompleteWithoutReview = async () => {
    try {
      setIsCompletingTrip(true);
      await onCompleteTrip(activeTrip.id);
      await saveOptionalFollowUp();
      setShowReviewModal(false);
      onNavigateRadar();
    } catch (error: any) {
      alert(error.message || (lang === 'pl' ? 'Nie udało się zakończyć wyjścia.' : 'Could not complete the outing.'));
    } finally {
      setIsCompletingTrip(false);
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-lg mx-auto pb-24">
      {/* Top Banner: Status & SOS Alert Button */}
      <div className="flex items-center justify-between bg-slate-900 border border-slate-800 p-3.5 rounded-2xl shadow-lg">
        <div className="flex items-center gap-2">
          <span
            className={`w-3 h-3 rounded-full ${
              activeTrip.sos_triggered
                ? 'bg-rose-500 animate-ping'
                : activeTrip.status === 'in_progress'
                ? 'bg-emerald-400 animate-pulse'
                : 'bg-amber-400'
            }`}
          />
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {t.tripStatus}
            </span>
            <h3 className="text-xs font-bold text-white">
              {activeTrip.sos_triggered
                ? t.statusSos
                : activeTrip.status === 'in_progress'
                ? t.statusShopping
                : t.statusAwaiting}
            </h3>
          </div>
        </div>

        {/* 1-Tap SOS Button */}
        <button
          onClick={() => {
            setShowSosModal(true);
            setSosConsentChecked(false);
            setSosError(null);
          }}
          className="bg-rose-500 hover:bg-rose-600 text-white font-black text-xs px-3.5 py-1.5 rounded-xl shadow-lg shadow-rose-500/30 flex items-center gap-1.5 cursor-pointer transition"
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>{t.sosBtn}</span>
        </button>
      </div>

      {/* Truthful Emergency SOS Active Banner */}
      {activeTrip.sos_triggered && (
        <div className="bg-rose-950/80 border-2 border-rose-600 rounded-3xl p-4 space-y-3 shadow-2xl">
          <div className="flex items-center gap-2.5 text-rose-300">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <div className="min-w-0 flex-1">
              <h4 className="text-xs font-black uppercase tracking-wider text-rose-200">{t.statusSos}</h4>
              <p className="text-[11px] text-rose-300 mt-0.5">
                {activeTrip.sos_alert?.delivery_confirmed
                  ? t.sosDelivered
                  : activeTrip.sos_alert?.status === 'dispatched'
                  ? t.sosDispatched
                  : t.sosFallbackNoDispatch}
              </p>
            </div>
          </div>

          {activeTrip.sos_alert?.emergency_contact && (
            <div className="p-2.5 bg-black/40 rounded-xl text-xs flex items-center justify-between">
              <span className="text-slate-300">Kontakt alarmowy:</span>
              <span className="font-mono font-bold text-rose-300">{activeTrip.sos_alert.emergency_contact}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 pt-1">
            <a
              href="tel:112"
              className="py-2.5 px-3 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 shadow-lg shadow-rose-900/40 text-center"
            >
              <span>🚨</span>
              <span>Zadzwoń 112</span>
            </a>
            {activeTrip.sos_alert?.direct_contact_url ? (
              <a
                href={activeTrip.sos_alert.direct_contact_url}
                className="py-2.5 px-3 bg-slate-800 hover:bg-slate-700 text-rose-300 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 border border-rose-700/60 text-center"
              >
                <span>📞</span>
                <span>Zadzwoń do bliskiego</span>
              </a>
            ) : (
              <a
                href="tel:112"
                className="py-2.5 px-3 bg-slate-800 hover:bg-slate-700 text-rose-300 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 border border-rose-700/60 text-center"
              >
                <span>📞</span>
                <span>Numer Alarmowy</span>
              </a>
            )}
          </div>
          <p className="text-[10px] text-rose-400/80 text-center leading-tight">
            {t.sosFooter}
          </p>
        </div>
      )}

      {/* Static planning suggestion: CartMate does not run a monitored countdown. */}
      <div className="bg-slate-950 border border-emerald-500/20 p-2.5 rounded-xl text-xs">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-slate-300">
            <Clock className="w-4 h-4 text-emerald-400" />
            <span>{t.safetyTimeRemaining}</span>
          </div>
          <span className="font-mono font-bold text-emerald-400">
            {activeTrip.safety_deadline_minutes || 45} min
          </span>
        </div>
        <p className="mt-1.5 text-[11px] text-slate-400">{t.safetyTimerDesc}</p>
      </div>

      {/* Specific Plan Card (What, When, Duration, Cost Policy & Mutual Acceptance) */}
      <div className={`p-4 rounded-3xl border transition shadow-xl space-y-3.5 ${
        isBothAccepted
          ? 'bg-slate-900/90 border-emerald-500/30'
          : 'bg-gradient-to-b from-amber-950/30 to-slate-900 border-amber-500/50'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className={`w-4 h-4 ${isBothAccepted ? 'text-emerald-400' : 'text-amber-400'}`} />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              {lang === 'pl' ? 'Plan spotkania' : 'Meeting Plan'}
            </h3>
          </div>
          {isBothAccepted ? (
            <span className="text-[10px] font-bold text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded-full border border-emerald-500/40 flex items-center gap-1">
              <Check className="w-3 h-3" />
              {lang === 'pl' ? 'Plan zaakceptowany' : 'Plan Accepted'}
            </span>
          ) : (
            <span className="text-[10px] font-bold text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded-full border border-amber-500/40 animate-pulse">
              {lang === 'pl' ? 'Oczekiwanie na akceptację' : 'Pending Acceptance'}
            </span>
          )}
        </div>

        {/* Plan Parameters Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 space-y-0.5">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">
              {lang === 'pl' ? 'Co robimy' : 'Activity'}
            </span>
            <span className="font-bold text-white truncate block">
              {activeTrip.plan_details?.what || activeTrip.destination_name}
            </span>
          </div>

          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 space-y-0.5">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">
              {lang === 'pl' ? 'Czas spotkania' : 'When & Duration'}
            </span>
            <span className="font-bold text-emerald-400 truncate block">
              {activeTrip.plan_details?.when || 'Zaraz po potwierdzeniu'} (~{activeTrip.plan_details?.estimated_duration_minutes || 45}m)
            </span>
          </div>

          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 space-y-0.5">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">
              {lang === 'pl' ? 'Zasada kosztów' : 'Cost Policy'}
            </span>
            <span className="font-bold text-teal-400 truncate block">
              {getCostPolicyLabel(activeTrip.plan_details?.cost_policy)}
            </span>
          </div>

          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 space-y-0.5">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">
              {lang === 'pl' ? 'Szacowany budżet' : 'Est. Budget'}
            </span>
            <span className="font-bold text-amber-300 truncate block">
              {activeTrip.plan_details?.estimated_cost_pln
                ? `${activeTrip.plan_details.estimated_cost_pln} PLN`
                : (lang === 'pl' ? 'Nie określono' : 'Not specified')}
            </span>
          </div>
        </div>

        {isHost && !['completed', 'cancelled'].includes(activeTrip.status) && (
          <form onSubmit={handleSavePlan} className="space-y-2 rounded-2xl border border-slate-700 bg-slate-950/70 p-3">
            <h4 className="text-xs font-bold text-white">{lang === 'pl' ? 'Ustal konkretny plan' : 'Set the concrete plan'}</h4>
            <label className="block text-[10px] text-slate-400">
              {lang === 'pl' ? 'Co robimy' : 'Activity'}
              <input
                required
                minLength={3}
                maxLength={140}
                value={planDraft.what}
                onChange={(event) => setPlanDraft((draft) => ({ ...draft, what: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white"
              />
            </label>
            <label className="block text-[10px] text-slate-400">
              {t.planWhenLabel}
              <input
                required
                minLength={3}
                maxLength={120}
                value={planDraft.when}
                onChange={(event) => setPlanDraft((draft) => ({ ...draft, when: event.target.value }))}
                placeholder={lang === 'pl' ? 'np. 27.09, 18:00' : 'e.g. 27 Sep, 18:00'}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-600"
              />
            </label>
            <label className="block text-[10px] text-slate-400">
              {t.planMeetingPointLabel}
              <input
                required
                minLength={8}
                maxLength={200}
                value={planDraft.meeting_point}
                onChange={(event) => setPlanDraft((draft) => ({ ...draft, meeting_point: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white"
              />
              <span className="mt-1 block leading-relaxed">{t.planMeetingPointHint}</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="block text-[10px] text-slate-400">
                {lang === 'pl' ? 'Czas (min)' : 'Duration (min)'}
                <input
                  type="number"
                  required
                  min={15}
                  max={240}
                  value={planDraft.estimated_duration_minutes}
                  onChange={(event) => setPlanDraft((draft) => ({ ...draft, estimated_duration_minutes: Number(event.target.value) }))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white"
                />
              </label>
              <label className="block text-[10px] text-slate-400">
                {lang === 'pl' ? 'Budżet szacunkowy (PLN)' : 'Budget estimate (PLN)'}
                <input
                  type="number"
                  min={0}
                  max={5000}
                  step="0.01"
                  value={planDraft.estimated_cost_pln}
                  disabled={planDraft.cost_policy === 'no_expected_spend' || planDraft.cost_policy === 'no_purchase_browse_only'}
                  onChange={(event) => setPlanDraft((draft) => ({ ...draft, estimated_cost_pln: Number(event.target.value) }))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white"
                />
              </label>
            </div>
            <label className="block text-[10px] text-slate-400">
              {lang === 'pl' ? 'Zasada kosztów' : 'Cost policy'}
              <select
                value={planDraft.cost_policy}
                onChange={(event) => setPlanDraft((draft) => ({
                  ...draft,
                  cost_policy: event.target.value,
                  estimated_cost_pln: ['no_expected_spend', 'no_purchase_browse_only'].includes(event.target.value) ? 0 : draft.estimated_cost_pln,
                }))}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white"
              >
                <option value="buyer_pays_own">{lang === 'pl' ? 'Każdy płaci za siebie' : 'Each pays for own items'}</option>
                <option value="split_strictly_50_50">{lang === 'pl' ? 'Podział 50/50' : 'Split 50/50'}</option>
                <option value="host_treats">{lang === 'pl' ? 'Gospodarz stawia' : 'Host treats'}</option>
                <option value="companion_treats">{lang === 'pl' ? 'Osoba towarzysząca stawia' : 'Companion treats'}</option>
                <option value="no_purchase_browse_only">{lang === 'pl' ? 'Spacer / oglądanie, bez zakupów' : 'Browse together, no purchase'}</option>
                <option value="no_expected_spend">{t.noExpectedSpend}</option>
              </select>
            </label>
            {planError && <p role="alert" className="text-[11px] text-rose-300">{planError}</p>}
            <button
              type="submit"
              disabled={isSavingPlan}
              className="w-full rounded-xl bg-slate-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
            >
              {isSavingPlan ? (lang === 'pl' ? 'Zapisywanie…' : 'Saving…') : (lang === 'pl' ? 'Zapisz plan i poproś o akceptację' : 'Save plan and request acceptance')}
            </button>
            <p className="text-[10px] text-slate-500">
              {lang === 'pl' ? 'Każda zmiana planu resetuje wcześniejsze akceptacje obu osób.' : 'Any plan edit resets both people’s earlier acceptances.'}
            </p>
          </form>
        )}

        {/* Mutual Acceptance Action / Notice */}
        {!isBothAccepted && (
          <div className="pt-1 space-y-2">
            {!(isHost ? activeTrip.host_accepted : activeTrip.companion_accepted) ? (
              <button
                onClick={handleAcceptPlanClick}
                disabled={isAcceptingPlan}
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-black text-xs py-3 rounded-2xl shadow-lg shadow-emerald-500/20 cursor-pointer transition flex items-center justify-center gap-1.5"
              >
                <Check className="w-4 h-4" />
                <span>
                  {isAcceptingPlan
                    ? (lang === 'pl' ? 'Zapisywanie akceptacji...' : 'Accepting...')
                    : (lang === 'pl' ? 'Akceptuję warunki spotkania ✓' : 'Accept Plan Terms ✓')}
                </span>
              </button>
            ) : (
              <div className="p-2.5 bg-amber-950/40 border border-amber-500/30 rounded-xl text-center text-xs text-amber-300">
                ⏳ {lang === 'pl'
                  ? `Oczekiwanie na akceptację ${isHost ? 'osoby towarzyszącej' : 'gospodarza'}.`
                  : `Waiting for the ${isHost ? 'companion' : 'host'} to accept the plan.`}
              </div>
            )}

            <p className="text-[10px] text-slate-400 text-center leading-tight">
              {lang === 'pl'
                ? 'Przejrzysty plan i brak niespodzianek cenowych to podstawa bezstresowego wyjścia. Obie strony muszą potwierdzić plan przed zameldowaniem.'
                : 'Clear plans and upfront expectations eliminate social friction. Both sides confirm before check-in.'}
            </p>
          </div>
        )}

        {/* Low-Guilt Cancellation Link */}
        <div className="flex items-center justify-between pt-1 border-t border-slate-800 text-[11px]">
          <span className="text-slate-500">
            {lang === 'pl' ? 'Zmieniły się plany?' : 'Plans changed?'}
          </span>
          <button
            type="button"
            onClick={() => setShowCancelModal(true)}
            className="text-rose-400 hover:text-rose-300 hover:underline cursor-pointer font-medium flex items-center gap-1 transition"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>{lang === 'pl' ? 'Zrezygnuj z wyjścia (bez poczucia winy)' : 'Cancel outing (no penalty)'}</span>
          </button>
        </div>
      </div>

      {/* Destination & Rendezvous Card */}
      <div className="bg-slate-900/90 border border-emerald-500/30 rounded-3xl p-4 space-y-3 shadow-xl">
        <div className="space-y-0.5">
          <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">
            {t.designatedDest}
          </span>
          <h2 className="text-lg font-black text-white">{activeTrip.destination_name}</h2>
        </div>

        <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 flex items-start gap-2.5">
          <MapPin className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <span className="text-xs font-bold text-slate-200">{t.rendezvousLabel}</span>
            <p className="text-xs text-slate-400">{activeTrip.rendezvous_spot}</p>
          </div>
        </div>

        {/* In-Store Check-In Status */}
        <div className="pt-1 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            <span>{t.checkinStatusLabel} </span>
            <span className="font-semibold text-slate-200">
              {activeTrip.host_checked_in && activeTrip.companion_checked_in
                ? t.checkinBoth
                : userCheckedIn
                ? t.checkinYou
                : t.checkinWaiting}
            </span>
          </div>
          {!userCheckedIn && (
            <button
              onClick={handleCheckInClick}
              disabled={isProcessing}
              className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs px-3.5 py-1.5 rounded-xl shadow-md cursor-pointer transition"
            >
              {isProcessing ? (lang === 'pl' ? 'Zapisywanie obecności…' : 'Recording check-in…') : t.arrivedBtn}
            </button>
          )}
        </div>
        <p className="pt-1 text-[10px] text-slate-500">
          {lang === 'pl' ? 'Obecność potwierdzasz samodzielnie; aplikacja nie sprawdza lokalizacji GPS.' : 'Check-in is self-reported; the app does not verify GPS location.'}
        </p>
      </div>

      {/* Mutual PIN Handshake (Open-Source Karrot/Foodsharing Feature) */}
      <div className={`p-4 rounded-3xl border transition shadow-lg space-y-3 ${
        isPinVerified
          ? 'bg-emerald-950/30 border-emerald-500/50'
          : 'bg-slate-900 border-amber-500/40'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <KeyRound className={`w-4 h-4 ${isPinVerified ? 'text-emerald-400' : 'text-amber-400'}`} />
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              {t.pinHandshakeTitle}
            </h3>
          </div>
          {isPinVerified && (
            <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1">
              <Check className="w-3 h-3" />
              {t.pinVerifiedBadge}
            </span>
          )}
        </div>

        <p className="text-[11px] text-slate-400">
          {t.pinHandshakeDesc}
        </p>

        {!isPinVerified ? (
          <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                  {currentUser.id === activeTrip.host.id
                    ? (lang === 'pl' ? 'Twój kod PIN do podania towarzyszowi:' : 'Your PIN to give companion:')
                    : (lang === 'pl' ? 'Wpisz PIN podany przez organizatora:' : 'Enter PIN given by host:')}
                </span>
                {currentUser.id === activeTrip.host.id ? (
                  <span className="font-mono text-xl font-black text-amber-400 tracking-widest">
                    {activeTrip.host_pin || '••••'}
                  </span>
                ) : (
                  <span className="text-xs text-slate-400 italic">
                    {lang === 'pl' ? 'Odbierz 4-cyfrowy kod na miejscu spotkania' : 'Ask companion in person at meeting point'}
                  </span>
                )}
              </div>
            </div>

            {isHost && (
              <p className="text-xs text-slate-400">
                {lang === 'pl'
                  ? 'Po Twoim zameldowaniu towarzysz wpisuje kod. Aplikacja nie sprawdza lokalizacji.'
                  : 'After your check-in, your companion enters this code. The app does not verify location.'}
              </p>
            )}
            {!isHost && (
            <form onSubmit={handleVerifyPinSubmit} className="flex gap-2">
              <input
                type="text"
                maxLength={4}
                value={enteredPin}
                onChange={(e) => setEnteredPin(e.target.value)}
                placeholder="0000"
                className="w-28 bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-center font-mono text-sm font-bold text-white placeholder-slate-600 focus:outline-none focus:border-amber-400"
              />
              <button
                type="submit"
                disabled={isProcessing || !enteredPin}
                className="flex-1 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl transition cursor-pointer shadow-md"
              >
                {isProcessing ? '...' : t.verifyPinBtn}
              </button>
            </form>
            )}
            {pinError && <p className="text-[10px] text-rose-400 font-medium">{pinError}</p>}
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-emerald-300 font-semibold bg-emerald-500/10 p-2.5 rounded-xl border border-emerald-500/20">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>{lang === 'pl' ? 'Organizator zameldował się, a towarzysz zweryfikował przekazany PIN. Aplikacja nie sprawdza lokalizacji.' : 'The host checked in and the companion verified the shared PIN. The app does not verify location.'}</span>
          </div>
        )}
      </div>

      {/* Wholesale & Grocery Splitter (Spliit Inspired Open-Source Feature) */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-4 space-y-3 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Receipt className="w-4 h-4 text-teal-400" />
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">{t.splitTabTitle}</h3>
              <p className="text-[10px] text-slate-400">{t.splitTabDesc}</p>
            </div>
          </div>
          {canRecordEqualSplit && (
            <button
              onClick={() => setShowAddSplitModal(true)}
              className="bg-teal-600 hover:bg-teal-500 text-white font-bold text-[11px] px-2.5 py-1 rounded-xl transition cursor-pointer flex items-center gap-1 shadow-md shadow-teal-950"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{lang === 'pl' ? 'Dodaj pozycję' : 'Record item'}</span>
            </button>
          )}
        </div>

        {!canRecordEqualSplit && (
          <p className="text-[10px] text-slate-400">
            {lang === 'pl'
              ? 'Kalkulator 50/50 działa wyłącznie po akceptacji takiej zasady przez obie osoby i rozpoczęciu wyjścia. Kwoty są deklarowane przez uczestników; aplikacja nie obsługuje płatności.'
              : 'The 50/50 calculator is available only after both people accept that policy and the outing starts. Amounts are user-reported; the app does not process payments.'}
          </p>
        )}

        {/* Split items list */}
        {(!activeTrip.items_split || activeTrip.items_split.length === 0) ? (
          <div className="bg-slate-950/60 p-3 rounded-2xl border border-slate-800/80 text-center">
            <p className="text-[11px] text-slate-400">{t.noItemsSplit}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {activeTrip.items_split.map((item) => (
              <div
                key={item.id}
                className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800/80 flex items-center justify-between text-xs"
              >
                <div>
                  <h5 className="font-bold text-slate-200">{item.item_name}</h5>
                  <span className="text-[10px] text-slate-400">
                    {lang === 'pl' ? 'Razem:' : 'Total:'} {item.total_price_pln.toFixed(2)} zł • {t.split5050}
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-black text-teal-400 block text-xs">
                    {(Math.floor(Math.round(item.total_price_pln * 100) / 2) / 100).toFixed(2)} zł
                  </span>
                  <span className="text-[9px] text-slate-400">
                    {item.payer_id === activeTrip.host.id ? t.companionOwes : t.hostOwes}
                  </span>
                </div>
              </div>
            ))}

            {/* User-declared net balance; CartMate never executes a payment. */}
            <div className="bg-gradient-to-r from-teal-950/50 to-slate-950 p-3 rounded-2xl border border-teal-500/30 mt-2 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                  {lang === 'pl' ? 'Suma podzielona' : 'Total Split'}
                </span>
                <span className="text-base font-black text-white">
                  {(activeTrip.total_split_pln || 0).toFixed(2)} zł
                </span>
              </div>

              {settlement?.debtor_id === currentUser.id && settlementCreditor && settlement.amount_pln > 0 && (
                <button
                  onClick={handleCopyBlik}
                  className="min-h-10 bg-slate-800 hover:bg-slate-700 text-teal-300 border border-teal-500/40 text-xs font-bold px-3 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-1.5"
                >
                  {copiedBlik ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedBlik ? t.blikCopied : t.settleBlikBtn}</span>
                </button>
              )}
              </div>
              <p className="text-xs font-semibold text-teal-200">
                {settlementDebtor && settlementCreditor && settlement && settlement.amount_pln > 0
                  ? `${settlementDebtor.name.split(' ')[0]} → ${settlementCreditor.name.split(' ')[0]}: ${settlement.amount_pln.toFixed(2)} zł`
                  : lang === 'pl' ? 'Brak kwoty do wyrównania.' : 'No net amount to reimburse.'}
              </p>
              <p className="text-[10px] text-slate-400">
                {lang === 'pl'
                  ? 'Kwoty podają uczestnicy. CartMate nie sprawdza paragonów ani nie wykonuje płatności.'
                  : 'Participants report these amounts. CartMate does not verify receipts or process payments.'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Companion Profile Card with Manner Temperature */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
            {t.companionHeader}
          </span>
          {/* Actions: Report & Block */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setShowReportModal(true)}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-amber-400 transition cursor-pointer"
              title={lang === 'pl' ? 'Zgłoś użytkownika' : 'Report user'}
            >
              <Flag className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setShowBlockModal(true)}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-rose-400 transition cursor-pointer"
              title={lang === 'pl' ? 'Zablokuj użytkownika' : 'Block user'}
            >
              <UserX className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <UserAvatar name={companion.name} src={companion.avatar} className="w-12 h-12 rounded-full border-2 border-emerald-500/40 text-sm" />
            <div>
              <div className="flex items-center gap-1.5">
                <h4 className="text-sm font-bold text-white">{companion.name}</h4>
                {companion.trust_tier === 'Gold' ? (
                  <span className="bg-amber-500/20 text-amber-300 text-[10px] font-bold px-1.5 py-0.5 rounded border border-amber-500/40">
                    {lang === 'pl' ? 'Złoty' : 'Gold'}
                  </span>
                ) : companion.is_id_verified ? (
                  <span className="bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-1.5 py-0.5 rounded border border-emerald-500/40">
                    {lang === 'pl' ? 'ID Zweryfikowany' : 'ID Verified'}
                  </span>
                ) : null}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-amber-400 font-bold flex items-center gap-0.5">
                  <Flame className="w-3.5 h-3.5 fill-amber-400 inline" />
                  {(companion.manner_temperature || 36.5).toFixed(1)}°C
                </span>
                <span className="text-xs text-slate-400">
                  • {companion.trips_completed} {lang === 'pl' ? 'wyjść' : 'runs'}
                </span>
              </div>
              {/* Public profile links; these do not imply identity verification. */}
              <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                {companion.instagram_handle && (
                  <span className="text-[10px] text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded-lg border border-rose-500/30 font-medium">
                    📸 {companion.instagram_handle}
                  </span>
                )}
                {companion.linkedin_handle && (
                  <span className="text-[10px] text-blue-300 bg-blue-500/10 px-2 py-0.5 rounded-lg border border-blue-500/30 font-medium">
                    💼 in/{companion.linkedin_handle}
                  </span>
                )}
                {companion.tiktok_handle && (
                  <span className="text-[10px] text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded-lg border border-cyan-500/30 font-medium">
                    🎵 {companion.tiktok_handle}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Live In-App Coordination Chat */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-4 space-y-3">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
          <MessageSquare className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-bold text-white">{t.chatHeader}</span>
        </div>

        {/* Message Thread */}
        <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
          {activeTrip.chat_room_id && messages.map((m, idx) => (
            <div
              key={m.id || idx}
              className={`p-2.5 rounded-2xl text-xs max-w-[85%] ${
                m.sender === 'You' || m.sender === 'Ty'
                  ? 'ml-auto bg-emerald-600/30 text-emerald-200 border border-emerald-500/40'
                  : 'bg-slate-950 text-slate-300 border border-slate-800'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-0.5">
                <span className="font-bold text-[10px] text-slate-400">{m.sender}</span>
                <span className="text-[9px] text-slate-500">{m.time}</span>
              </div>
              <p>{m.text}</p>
            </div>
          ))}
          {!activeTrip.chat_room_id && (
            <p className="text-xs text-slate-500">{lang === 'pl' ? 'Czat nie jest dostępny dla tego starszego wyjścia.' : 'Chat is unavailable for this legacy trip.'}</p>
          )}
          {chatError && <p role="alert" className="text-xs text-rose-300">{chatError}</p>}
        </div>

        {/* Input */}
        <form onSubmit={handleSendMessage} className="flex gap-2 pt-1">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder={t.chatPlaceholder}
            maxLength={2000}
            disabled={!activeTrip.chat_room_id || isSendingChat}
            aria-label={t.chatPlaceholder}
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
          <button
            type="submit"
            disabled={!activeTrip.chat_room_id || isSendingChat || !newMessage.trim()}
            className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 p-2 rounded-xl transition cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* Complete Trip Action */}
      <button
        onClick={handleFinishOuting}
        className="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-black text-xs py-3.5 rounded-2xl transition cursor-pointer flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20"
      >
        <CheckCircle2 className="w-4 h-4" />
        <span>{t.finishOutingBtn}</span>
      </button>

      {/* Add Split Item Modal */}
      {showAddSplitModal && (
        <div id="trip-split-dialog" role="dialog" aria-modal="true" aria-labelledby="trip-split-title" tabIndex={-1} className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-teal-500/60 w-full max-w-sm rounded-3xl p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 id="trip-split-title" className="text-sm font-bold text-white flex items-center gap-2">
                <Receipt className="w-4 h-4 text-teal-400" />
                <span>{t.addItemSplitBtn}</span>
              </h3>
              <button
                type="button"
                aria-label={t.cancel}
                onClick={() => setShowAddSplitModal(false)}
                className="text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddSplitItem} className="space-y-3">
              <div>
                <label htmlFor="trip-split-item-name" className="text-[11px] font-semibold text-slate-300 block mb-1">
                  {t.itemNameLabel}
                </label>
                <input
                  id="trip-split-item-name"
                  type="text"
                  required
                  value={splitItemName}
                  onChange={(e) => setSplitItemName(e.target.value)}
                  placeholder="np. Zgrzewka San Pellegrino 6x1L"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div>
                <label htmlFor="trip-split-item-price" className="text-[11px] font-semibold text-slate-300 block mb-1">
                  {t.itemPriceLabel}
                </label>
                <input
                  id="trip-split-item-price"
                  type="number"
                  step="0.01"
                  required
                  value={splitItemPrice}
                  onChange={(e) => setSplitItemPrice(e.target.value)}
                  placeholder="34.90"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-[11px] text-teal-300">
                {lang === 'pl'
                  ? 'To tylko zapis pozycji i wyliczenie 50/50 — CartMate nie weryfikuje paragonu ani nie przenosi pieniędzy.'
                  : 'This records an item and calculates an even split only; CartMate does not verify receipts or move money.'}
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddSplitModal(false)}
                  className="flex-1 py-2 rounded-xl border border-slate-700 text-slate-300 text-xs font-semibold hover:bg-slate-800 cursor-pointer"
                >
                  {t.cancel}
                </button>
                <button
                  type="submit"
                  disabled={isProcessing}
                  className="flex-1 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold shadow-md cursor-pointer"
                >
                  {lang === 'pl' ? 'Zapisz pozycję' : 'Record item'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SOS Confirmation Modal (Truthful & Explicit Consent) */}
      {showSosModal && (
        <div
          id="trip-sos-dialog"
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="trip-help-options-title"
          tabIndex={-1}
        >
          <div className="bg-[#0f172a] border border-rose-500/60 w-full max-w-sm rounded-3xl p-5 space-y-4 shadow-2xl text-left">
            <div className="w-14 h-14 rounded-2xl bg-rose-500/20 text-rose-400 border border-rose-500/40 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-7 h-7" />
            </div>
            <div className="space-y-1.5 text-center">
              <h3 id="trip-help-options-title" className="text-base font-black text-white">{t.sosModalTitle}</h3>
              <p className="text-xs text-slate-300">
                {t.sosModalDesc}
              </p>
              <div className="bg-slate-950 p-2.5 rounded-lg text-xs font-bold text-rose-300 mt-2 text-center">
                {currentUser.emergency_contact
                  ? (lang === 'pl' ? 'Zapisany kontakt nie zostanie automatycznie powiadomiony.' : 'Your saved contact will not be notified automatically.')
                  : (lang === 'pl' ? 'Brak skonfigurowanego kontaktu. W razie zagrożenia zadzwoń pod 112.' : 'No contact is configured. Call 112 in an emergency.')}
              </div>
            </div>

            {sosError && (
              <div className="p-2.5 text-xs bg-rose-950/80 border border-rose-800 text-rose-300 rounded-lg">
                ⚠️ {sosError}
              </div>
            )}

            {/* Explicit User Consent Checkbox */}
            <label className="flex items-start gap-2.5 p-3 bg-slate-950/70 border border-rose-900/40 rounded-xl cursor-pointer">
              <input
                type="checkbox"
                checked={sosConsentChecked}
                onChange={(e) => {
                  setSosConsentChecked(e.target.checked);
                  setSosError(null);
                }}
                className="mt-0.5 rounded text-rose-500 focus:ring-rose-500 cursor-pointer"
              />
              <span className="text-[11px] text-slate-300 leading-snug">
                {t.sosConsentLabel}
              </span>
            </label>

            <div className="flex gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => {
                  setShowSosModal(false);
                  setSosConsentChecked(false);
                  setSosError(null);
                }}
                className="flex-1 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-bold hover:bg-slate-800 cursor-pointer"
              >
                {t.cancel}
              </button>
              <button
                type="button"
                disabled={!sosConsentChecked || isSosDispatching}
                onClick={handleSosClick}
                className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold shadow-lg shadow-rose-600/30 cursor-pointer transition"
              >
                {isSosDispatching ? t.sosOpeningLabel : t.sosConfirmBtn}
              </button>
            </div>

            <div className="pt-2 border-t border-slate-800/60 text-center">
              <a
                href="tel:112"
                className="text-[11px] text-rose-400 hover:underline inline-flex items-center gap-1 font-semibold"
              >
                <span>🚨 Bezpośrednie zagrożenie życia? Zadzwoń na 112</span>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Post-Trip Manner Temperature Review Modal (Karrot/Daangn Inspired) */}
      {showReviewModal && (
        <div id="trip-review-dialog" role="dialog" aria-modal="true" aria-labelledby="trip-review-title" tabIndex={-1} className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-emerald-500/50 w-full max-w-sm rounded-3xl p-5 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div className="space-y-1 text-center">
              <h3 id="trip-review-title" className="text-base font-bold text-white">{t.completedOutingTitle}</h3>
              <p className="text-xs text-slate-400">{t.completedOutingDesc} {companion.name}</p>
            </div>

            {/* Stars */}
            <div className="flex justify-center gap-2 text-2xl text-amber-400 py-1">
              {[1, 2, 3, 4, 5].map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-label={`${s} / 5`}
                  aria-pressed={reviewRating === s}
                  onClick={() => setReviewRating(s)}
                  className="cursor-pointer hover:scale-110 transition"
                >
                  {s <= reviewRating ? '★' : '☆'}
                </button>
              ))}
            </div>

            {/* Contextual Manner Badges (Karrot/Daangn Style) */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-semibold text-slate-300 block">
                {lang === 'pl' ? 'Wybierz odznaki kultury (podnoszą Temperaturę):' : 'Select manner badges (raises temperature):'}
              </span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  t.mannerBadgesPunctual,
                  t.mannerBadgesPolite,
                  t.mannerBadgesQuickSplit,
                  t.mannerBadgesHelpful,
                ].map((b) => {
                  const isSelected = selectedBadges.includes(b);
                  return (
                    <button
                      key={b}
                      type="button"
                      onClick={() => handleToggleBadge(b)}
                      className={`text-[11px] font-semibold px-2.5 py-1 rounded-xl border transition cursor-pointer ${
                        isSelected
                          ? 'bg-amber-500/20 border-amber-400 text-amber-300'
                          : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-500'
                      }`}
                    >
                      {b}
                    </button>
                  );
                })}
              </div>
            </div>

            <textarea
              aria-label={t.outingCommentLabel}
              rows={2}
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />

            {/* Mutual meet-again choice; private until both opt in. */}
            <div className="bg-slate-950 p-3 rounded-2xl border border-indigo-500/30 space-y-2 text-left">
              <div className="flex items-center gap-1.5 text-xs font-bold text-white">
                <HeartHandshake className="w-4 h-4 text-indigo-400" />
                <span>
                  {t.meetAgainPrompt} {companion.name}?
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  aria-pressed={wouldMeetAgain === true}
                  onClick={() => setWouldMeetAgain(true)}
                  className={`py-2 px-2.5 rounded-xl text-xs font-bold border transition cursor-pointer flex items-center justify-center gap-1.5 ${
                    wouldMeetAgain
                      ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 shadow-md'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <span>🤝</span>
                  <span>{lang === 'pl' ? 'Tak, chętnie!' : 'Yes, buddy!'}</span>
                </button>
                <button
                  type="button"
                  aria-pressed={wouldMeetAgain === false}
                  onClick={() => setWouldMeetAgain(false)}
                  className={`py-2 px-2.5 rounded-xl text-xs font-bold border transition cursor-pointer flex items-center justify-center gap-1.5 ${
                    wouldMeetAgain === false
                      ? 'bg-slate-800 border-slate-600 text-slate-300'
                      : 'bg-slate-900 border-slate-800 text-slate-500 hover:border-slate-700'
                  }`}
                >
                  <span>👋</span>
                  <span>{lang === 'pl' ? 'Tylko jednorazowo' : 'One-time only'}</span>
                </button>
              </div>
              {/* Vibe tags selector */}
              {wouldMeetAgain && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] text-slate-300 block font-semibold">
                    {lang === 'pl' ? 'Co najbardziej doceniasz we wspólnym wyjściu?' : 'What did you appreciate most?'}
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      lang === 'pl' ? 'Punktualność' : 'Punctual',
                      lang === 'pl' ? 'Dobre planowanie' : 'Good planning',
                      lang === 'pl' ? 'Miła rozmowa' : 'Good Chat',
                      lang === 'pl' ? 'Bezpieczna atmosfera' : 'Safe Vibe',
                    ].map((tag) => {
                      const isSel = followUpVibeTags.includes(tag);
                      return (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => {
                            if (isSel) {
                              setFollowUpVibeTags(followUpVibeTags.filter((t) => t !== tag));
                            } else {
                              setFollowUpVibeTags([...followUpVibeTags, tag]);
                            }
                          }}
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-lg border transition cursor-pointer ${
                            isSel
                              ? 'bg-indigo-500/20 border-indigo-400 text-indigo-300'
                              : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                          }`}
                        >
                          {tag}
                        </button>
                      );
                    })}
                  </div>

                  <input
                    type="text"
                    value={followUpFeedback}
                    onChange={(e) => setFollowUpFeedback(e.target.value)}
                    placeholder={lang === 'pl' ? 'Opcjonalna prywatna notatka...' : 'Optional private note...'}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <p className="text-[10px] text-slate-400">
                {t.meetAgainOptional}
              </p>
            </div>

            <div className="space-y-2">
              <button
                type="button"
                onClick={handleSubmitReview}
                disabled={reviewRating < 1 || isCompletingTrip}
                className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-3 rounded-xl shadow-md cursor-pointer transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t.submitReviewBtn}
              </button>
              <button
                type="button"
                onClick={handleCompleteWithoutReview}
                disabled={isCompletingTrip}
                className="w-full rounded-xl border border-slate-700 px-3 py-3 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-50"
              >
                {t.finishWithoutReviewBtn}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Low-Guilt Cancellation Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          <div id="trip-cancel-dialog" role="dialog" aria-modal="true" aria-labelledby="cancel-trip-title" tabIndex={-1} className="bg-[#0f172a] border border-slate-700 w-full max-w-sm rounded-3xl p-5 space-y-4 shadow-2xl text-left">
            <div className="w-12 h-12 rounded-2xl bg-slate-800 text-slate-300 border border-slate-700 flex items-center justify-center mx-auto">
              <XCircle className="w-6 h-6 text-slate-400" />
            </div>

            <div className="space-y-1 text-center">
              <h3 id="cancel-trip-title" className="text-base font-bold text-white">
                {lang === 'pl' ? 'Zrezygnuj z wyjścia' : 'Cancel Outing'}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {lang === 'pl'
                  ? 'Rozumiemy to — plany i samopoczucie bywają zmienne. Twoja Temperatura Kultury Manner nie zostanie obniżona.'
                  : 'Plans change and life happens. Your Manner Temperature will not be penalized.'}
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-slate-300 block">
                {lang === 'pl' ? 'Wybierz powód rezygnacji:' : 'Select reason:'}
              </label>
              {[
                { id: 'changed_mind', label: lang === 'pl' ? 'Zmieniły mi się plany' : 'Changed my mind' },
                { id: 'scheduling_conflict', label: lang === 'pl' ? 'Kolidujący termin / pilna sprawa' : 'Scheduling conflict' },
                { id: 'bad_weather', label: lang === 'pl' ? 'Pogoda lub trudności z dojazdem' : 'Bad weather / transit issues' },
                { id: 'emergency', label: lang === 'pl' ? 'Nagła sytuacja' : 'Emergency' },
                { id: 'no_longer_needed', label: t.noLongerNeeded },
                { id: 'other', label: lang === 'pl' ? 'Inny powód' : 'Other' },
              ].map((r) => (
                <label
                  key={r.id}
                  onClick={() => setCancelReason(r.id)}
                  className={`flex items-center gap-2.5 p-2.5 rounded-xl border text-xs cursor-pointer transition ${
                    cancelReason === r.id
                      ? 'bg-slate-800 border-emerald-500/60 text-white font-medium'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <input
                    type="radio"
                    name="cancel_reason"
                    checked={cancelReason === r.id}
                    onChange={() => setCancelReason(r.id)}
                    className="text-emerald-500 focus:ring-emerald-500"
                  />
                  <span>{r.label}</span>
                </label>
              ))}
            </div>

            <div>
              <label htmlFor="trip-cancel-note" className="text-[11px] font-semibold text-slate-300 block mb-1">
                {lang === 'pl' ? 'Dodatkowa wiadomość (opcjonalnie):' : 'Optional note:'}
              </label>
              <textarea
                id="trip-cancel-note"
                rows={2}
                value={cancelNote}
                onChange={(e) => setCancelNote(e.target.value)}
                placeholder={lang === 'pl' ? 'Przepraszam, wyskoczyło mi coś nagłego...' : 'Sorry, something came up...'}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
              />
            </div>

            <div className="flex gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => setShowCancelModal(false)}
                className="flex-1 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-bold hover:bg-slate-800 cursor-pointer"
              >
                {t.cancel}
              </button>
              <button
                type="button"
                disabled={isCancelling}
                onClick={handleConfirmCancelTrip}
                className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-rose-900/40 cursor-pointer transition"
              >
                {isCancelling ? '...' : (lang === 'pl' ? 'Potwierdź rezygnację' : 'Confirm Cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Human Moderation Report Modal */}
      {showReportModal && (
        <div id="trip-report-dialog" role="dialog" aria-modal="true" aria-labelledby="trip-report-title" tabIndex={-1} className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-amber-500/40 w-full max-w-sm rounded-3xl p-5 space-y-4 shadow-2xl text-left">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center justify-center mx-auto">
              <Flag className="w-6 h-6" />
            </div>

            <div className="space-y-1 text-center">
              <h3 id="trip-report-title" className="text-base font-bold text-white">
                {lang === 'pl' ? 'Zgłoś zachowanie użytkownika' : 'Report User Behavior'}
              </h3>
              <p className="text-xs text-slate-400">
                {lang === 'pl'
                  ? 'Zgłoszenie trafi do kolejki. Nie jest ona monitorowana całodobowo; w nagłym zagrożeniu zadzwoń pod 112.'
                  : 'Your report goes into a queue, not a 24/7 monitored service. Call 112 in an emergency.'}
              </p>
            </div>

            {reportSuccessMessage ? (
              <div className="p-3 bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 rounded-xl text-xs text-center font-medium">
                ✓ {reportSuccessMessage}
              </div>
            ) : (
              <form onSubmit={handleConfirmReport} className="space-y-3">
                <div>
                  <label htmlFor="trip-report-category" className="text-[11px] font-semibold text-slate-300 block mb-1">
                    {lang === 'pl' ? 'Kategoria naruszenia:' : 'Violation category:'}
                  </label>
                  <select
                    id="trip-report-category"
                    value={reportCategory}
                    onChange={(e) => setReportCategory(e.target.value as ReportCategory)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-amber-400"
                  >
                    <option value="harassment">{lang === 'pl' ? 'Nękanie / obraźliwe zachowanie' : 'Harassment'}</option>
                    <option value="unsafe_behavior">{lang === 'pl' ? 'Niebezpieczne zachowanie' : 'Unsafe behavior'}</option>
                    <option value="no_show">{lang === 'pl' ? 'Brak obecności (No-show)' : 'No-show'}</option>
                    <option value="safety_risk">{lang === 'pl' ? 'Zagrożenie bezpieczeństwa' : 'Safety risk'}</option>
                    <option value="spam">{lang === 'pl' ? 'Spam handlowy / reklama' : 'Spam'}</option>
                    <option value="fake_profile">{lang === 'pl' ? 'Fałszywy profil / wprowadzanie w błąd' : 'Fake profile / misrepresentation'}</option>
                    <option value="financial_fraud">{lang === 'pl' ? 'Oszustwo finansowe' : 'Financial fraud'}</option>
                    <option value="other">{lang === 'pl' ? 'Inny powód' : 'Other'}</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="trip-report-details" className="text-[11px] font-semibold text-slate-300 block mb-1">
                    {lang === 'pl' ? 'Opis sytuacji (fakty):' : 'Details:'}
                  </label>
                  <textarea
                    id="trip-report-details"
                    rows={3}
                    required
                    value={reportDetails}
                    onChange={(e) => setReportDetails(e.target.value)}
                    placeholder={lang === 'pl' ? 'Opisz co się wydarzyło...' : 'Describe what happened...'}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                  />
                </div>

                <div className="flex gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowReportModal(false)}
                    className="flex-1 py-2 rounded-xl border border-slate-700 text-slate-300 text-xs font-semibold hover:bg-slate-800 cursor-pointer"
                  >
                    {t.cancel}
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingReport}
                    className="flex-1 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold shadow-md cursor-pointer"
                  >
                    {isSubmittingReport ? '...' : (lang === 'pl' ? 'Wyślij zgłoszenie' : 'Submit Report')}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Block User Modal */}
      {showBlockModal && (
        <div id="trip-block-dialog" role="dialog" aria-modal="true" aria-labelledby="trip-block-title" tabIndex={-1} className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-rose-500/40 w-full max-w-sm rounded-3xl p-5 space-y-4 shadow-2xl text-left">
            <div className="w-12 h-12 rounded-2xl bg-rose-500/20 text-rose-400 border border-rose-500/40 flex items-center justify-center mx-auto">
              <UserX className="w-6 h-6" />
            </div>

            <div className="space-y-1 text-center">
              <h3 id="trip-block-title" className="text-base font-bold text-white">
                {lang === 'pl' ? `Zablokuj ${companion.name}` : `Block ${companion.name}`}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {lang === 'pl'
                  ? 'Blokada jest dwustronna: użytkownik nie otrzyma powiadomienia, a Wasze profile, wyjścia i wiadomości staną się dla siebie całkowicie niewidoczne.'
                  : 'Blocking is strictly bidirectional: the user will not be notified, and all pings, profiles, and chats will be hidden.'}
              </p>
            </div>

            <div>
              <label htmlFor="trip-block-reason" className="text-[11px] font-semibold text-slate-300 block mb-1">
                {lang === 'pl' ? 'Powód blokady (opcjonalnie):' : 'Reason (optional):'}
              </label>
              <input
                id="trip-block-reason"
                type="text"
                value={blockReason}
                onChange={(e) => setBlockReason(e.target.value)}
                placeholder={lang === 'pl' ? 'np. Natarczywe zachowanie' : 'e.g. Uncomfortable vibe'}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500"
              />
            </div>

            <div className="flex gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => setShowBlockModal(false)}
                className="flex-1 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-bold hover:bg-slate-800 cursor-pointer"
              >
                {t.cancel}
              </button>
              <button
                type="button"
                disabled={isBlocking}
                onClick={handleConfirmBlock}
                className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-lg shadow-rose-900/40 cursor-pointer transition"
              >
                {isBlocking ? '...' : (lang === 'pl' ? 'Zablokuj użytkownika' : 'Block User')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
