import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ClipboardCheck, LoaderCircle, RefreshCw, ShieldAlert } from 'lucide-react';
import type { Language } from '../locales';
import type { ModerationAction, ReportSchema } from '../types';
import { fetchModerationQueue, submitModerationAction } from '../api';

interface ModeratorConsoleProps {
  lang: Language;
  onBack: () => void;
}

const actionOptions: ModerationAction[] = ['dismiss', 'warn', 'suspend', 'ban'];

export const ModeratorConsole: React.FC<ModeratorConsoleProps> = ({ lang, onBack }) => {
  const isPolish = lang === 'pl';
  const [reports, setReports] = useState<ReportSchema[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [action, setAction] = useState<ModerationAction>('dismiss');
  const [note, setNote] = useState('');
  const [confirmDestructive, setConfirmDestructive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadQueue = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setError(null);
    }
    try {
      const queue = await fetchModerationQueue();
      setReports(queue);
      setSelectedId((current) => current && queue.some((report) => report.id === current)
        ? current
        : queue[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load the queue.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchModerationQueue()
      .then((queue) => {
        if (!cancelled) {
          setReports(queue);
          setSelectedId(queue[0]?.id ?? null);
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Could not load the queue.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const selectedReport = reports.find((report) => report.id === selectedId) ?? null;

  const handleAction = async () => {
    if (!selectedReport || !note.trim()) return;
    if ((action === 'suspend' || action === 'ban') && !confirmDestructive) {
      setConfirmDestructive(true);
      return;
    }

    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const resolved = await submitModerationAction(selectedReport.id, action, note.trim());
      const remaining = reports.filter((report) => report.id !== resolved.id);
      setReports(remaining);
      setSelectedId(remaining[0]?.id ?? null);
      setAction('dismiss');
      setNote('');
      setConfirmDestructive(false);
      setMessage(isPolish ? 'Decyzja została zapisana.' : 'Decision recorded.');
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not submit the decision.');
      setConfirmDestructive(false);
    } finally {
      setSubmitting(false);
    }
  };

  const actionLabel = (value: ModerationAction) => {
    if (isPolish) {
      return {
        dismiss: 'Odrzuć zgłoszenie',
        warn: 'Zapisz ostrzeżenie wewnętrzne (bez powiadomienia)',
        suspend: 'Zawieś konto',
        ban: 'Zbanuj konto',
      }[value];
    }
    return {
      dismiss: 'Dismiss report',
      warn: 'Record internal warning (no user notice)',
      suspend: 'Suspend account',
      ban: 'Ban account',
    }[value];
  };

  return (
    <section className="mx-auto max-w-lg space-y-4 p-4 pb-24" aria-labelledby="moderation-title">
      <header className="flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded-xl border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"
          aria-label={isPolish ? 'Wróć do profilu' : 'Back to profile'}
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </button>
        <div>
          <h2 id="moderation-title" className="text-lg font-bold text-white">
            {isPolish ? 'Kolejka bezpieczeństwa' : 'Safety review queue'}
          </h2>
          <p className="text-xs text-slate-400">
            {isPolish ? 'Każde zgłoszenie ocenia człowiek. Kolejność: najstarsze najpierw.' : 'Human review only. Oldest reports appear first.'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadQueue()}
          disabled={loading}
          className="ml-auto rounded-xl border border-slate-700 p-2 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          aria-label={isPolish ? 'Odśwież kolejkę' : 'Refresh queue'}
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
        </button>
      </header>

      {error && <p role="alert" className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-sm text-rose-200">{error}</p>}
      {message && <p role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-3 text-sm text-emerald-200">{message}</p>}

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-12 text-slate-300" role="status">
          <LoaderCircle className="h-5 w-5 animate-spin" aria-hidden="true" />
          {isPolish ? 'Ładowanie zgłoszeń…' : 'Loading reports…'}
        </div>
      ) : reports.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
          <ClipboardCheck className="mx-auto mb-3 h-8 w-8 text-emerald-400" aria-hidden="true" />
          <p className="font-semibold text-white">{isPolish ? 'Kolejka jest pusta' : 'The queue is clear'}</p>
          <p className="mt-1 text-sm text-slate-400">{isPolish ? 'Nie ma oczekujących zgłoszeń.' : 'There are no pending reports.'}</p>
        </div>
      ) : (
        <>
          <ol className="space-y-2" aria-label={isPolish ? 'Oczekujące zgłoszenia' : 'Pending reports'}>
            {reports.map((report) => (
              <li key={report.id}>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedId(report.id);
                    setAction('dismiss');
                    setNote('');
                    setConfirmDestructive(false);
                    setMessage(null);
                  }}
                  aria-pressed={selectedId === report.id}
                  className={`w-full rounded-xl border p-3 text-left ${selectedId === report.id ? 'border-amber-400/70 bg-amber-400/10' : 'border-slate-800 bg-slate-900 hover:border-slate-700'}`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-white">{report.category.replaceAll('_', ' ')}</span>
                    <span className="text-xs text-slate-400">{new Date(report.created_at).toLocaleString(lang)}</span>
                  </span>
                  <span className="mt-1 block text-xs text-slate-400">
                    {isPolish ? 'Zgłaszany użytkownik' : 'Reported user'}: {report.reported_user_id}
                  </span>
                </button>
              </li>
            ))}
          </ol>

          {selectedReport && (
            <article className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900 p-4" aria-labelledby="report-details-title">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-amber-300" aria-hidden="true" />
                <h3 id="report-details-title" className="font-bold text-white">
                  {isPolish ? 'Szczegóły zgłoszenia' : 'Report details'}
                </h3>
              </div>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                <dt className="text-slate-400">ID</dt><dd className="break-all text-slate-200">{selectedReport.id}</dd>
                <dt className="text-slate-400">{isPolish ? 'Zgłaszający' : 'Reporter'}</dt><dd className="break-all text-slate-200">{selectedReport.reporter_id}</dd>
                {selectedReport.trip_id && <><dt className="text-slate-400">{isPolish ? 'Wyjście' : 'Outing'}</dt><dd className="break-all text-slate-200">{selectedReport.trip_id}</dd></>}
              </dl>
              <p className="whitespace-pre-wrap break-words rounded-xl bg-slate-950/70 p-3 text-sm leading-relaxed text-slate-200">{selectedReport.details}</p>

              <div className="space-y-3 border-t border-slate-800 pt-4">
                <label htmlFor="moderation-action" className="block text-sm font-semibold text-slate-200">
                  {isPolish ? 'Decyzja' : 'Decision'}
                </label>
                <select
                  id="moderation-action"
                  value={action}
                  onChange={(event) => {
                    setAction(event.target.value as ModerationAction);
                    setConfirmDestructive(false);
                  }}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white"
                >
                  {actionOptions.map((option) => <option key={option} value={option}>{actionLabel(option)}</option>)}
                </select>
                <label htmlFor="moderation-note" className="block text-sm font-semibold text-slate-200">
                  {isPolish ? 'Notatka uzasadniająca (wymagana)' : 'Reasoning note (required)'}
                </label>
                <textarea
                  id="moderation-note"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  required
                  rows={3}
                  maxLength={1000}
                  className="w-full resize-y rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-sm text-white placeholder:text-slate-500"
                  placeholder={isPolish ? 'Zapisz krótko powód decyzji.' : 'Briefly record the reason for this decision.'}
                />
                {confirmDestructive && (
                  <p role="alert" className="rounded-xl border border-rose-500/40 bg-rose-950/30 p-3 text-sm text-rose-200">
                    {isPolish ? `Potwierdź nieodwracalną decyzję: „${actionLabel(action)}”.` : `Confirm this serious account action: “${actionLabel(action)}”.`}
                  </p>
                )}
                <div className="flex gap-2">
                  {confirmDestructive && (
                    <button
                      type="button"
                      onClick={() => setConfirmDestructive(false)}
                      className="flex-1 rounded-xl border border-slate-700 px-3 py-3 text-sm font-semibold text-slate-200"
                    >
                      {isPolish ? 'Wróć' : 'Go back'}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void handleAction()}
                    disabled={submitting || !note.trim()}
                    className={`flex-1 rounded-xl px-3 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50 ${action === 'ban' || action === 'suspend' ? 'bg-rose-700 hover:bg-rose-600' : 'bg-emerald-700 hover:bg-emerald-600'}`}
                  >
                    {submitting ? (isPolish ? 'Zapisywanie…' : 'Saving…') : confirmDestructive ? (isPolish ? 'Potwierdź decyzję' : 'Confirm decision') : actionLabel(action)}
                  </button>
                </div>
              </div>
            </article>
          )}
        </>
      )}
    </section>
  );
};
