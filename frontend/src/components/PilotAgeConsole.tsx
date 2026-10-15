import { useState } from 'react';
import type { FormEvent } from 'react';
import { attestPilotAdult } from '../api';
import type { PilotAgeCheckMethod } from '../api';
import type { Language } from '../locales';

interface PilotAgeConsoleProps {
  lang: Language;
}

/** Staging-only human workflow. The server still enforces moderator and pilot gates. */
export function PilotAgeConsole({ lang }: PilotAgeConsoleProps) {
  const pl = lang === 'pl';
  const [subjectId, setSubjectId] = useState('');
  const [accountChallenge, setAccountChallenge] = useState('');
  const [method, setMethod] = useState<PilotAgeCheckMethod>('mdowod_qr');
  const [adult, setAdult] = useState(false);
  const [present, setPresent] = useState(false);
  const [consented, setConsented] = useState(false);
  const [bound, setBound] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!subjectId.trim() || !accountChallenge.trim() || !adult || !present || !consented || !bound || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const confirmation = await attestPilotAdult(subjectId.trim(), method, accountChallenge.trim());
      setResult(pl
        ? `Potwierdzenie 18+ zapisano do ${new Date(confirmation.expires_at).toLocaleString('pl-PL')}.`
        : `18+ check recorded until ${new Date(confirmation.expires_at).toLocaleString()}.`);
      setSubjectId('');
      setAccountChallenge('');
      setAdult(false);
      setPresent(false);
      setConsented(false);
      setBound(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Age check failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="pilot-age-title" className="rounded-2xl border border-sky-600/40 bg-sky-950/30 p-4 text-left space-y-3">
      <h2 id="pilot-age-title" className="text-base font-bold text-sky-100">
        {pl ? 'Weryfikacja 18+ — operator pilotażu' : '18+ verification — pilot operator'}
      </h2>
      <p className="text-xs leading-relaxed text-slate-300">
        {pl
          ? 'Tylko po osobistym sprawdzeniu na żywo: kryptograficzny kod QR mDowodu lub oryginalny dokument tożsamości. Nie przyjmuj zdjęć, zrzutów ekranu ani danych dokumentu w CartMate.'
          : 'Only after a live, in-person check: the cryptographic mDowód QR or an original identity document. Do not accept photos or screenshots, or enter document data into CartMate.'}
      </p>
      <a
        href="https://weryfikator.mobywatel.gov.pl/verification-process"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block text-xs font-semibold text-sky-300 underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
      >
        {pl ? 'Otwórz oficjalny weryfikator mDowodu' : 'Open official mDowód verifier'}
      </a>
      <form onSubmit={(event) => { void submit(event); }} className="space-y-3">
        <label className="block text-xs font-semibold text-slate-200" htmlFor="pilot-age-subject-id">
          {pl ? 'Kod konta osoby sprawdzanej' : 'Account code of person being checked'}
        </label>
        <input
          id="pilot-age-subject-id"
          type="text"
          required
          autoCapitalize="off"
          autoComplete="off"
          value={subjectId}
          onChange={(event) => setSubjectId(event.target.value)}
          placeholder="usr_..."
          className="w-full rounded-xl border border-slate-600 bg-slate-950 px-3 py-3 text-sm text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
        />
        <label className="block text-xs font-semibold text-slate-200" htmlFor="pilot-age-challenge">
          {pl ? 'Jednorazowy kod z zalogowanego konta (ważny 5 minut)' : 'One-use code from the signed-in account (valid 5 minutes)'}
        </label>
        <input
          id="pilot-age-challenge"
          type="text"
          required
          minLength={10}
          maxLength={64}
          autoCapitalize="off"
          autoComplete="off"
          value={accountChallenge}
          onChange={(event) => setAccountChallenge(event.target.value)}
          className="w-full rounded-xl border border-slate-600 bg-slate-950 px-3 py-3 text-sm text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
        />
        <label className="block text-xs font-semibold text-slate-200" htmlFor="pilot-age-method">
          {pl ? 'Metoda sprawdzenia' : 'Check method'}
        </label>
        <select
          id="pilot-age-method"
          value={method}
          onChange={(event) => setMethod(event.target.value as PilotAgeCheckMethod)}
          className="w-full rounded-xl border border-slate-600 bg-slate-950 px-3 py-3 text-sm text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
        >
          <option value="mdowod_qr">mDowód QR — official verifier</option>
          <option value="physical_identity_document">{pl ? 'Oryginalny dokument, osobiście' : 'Original ID, in person'}</option>
        </select>
        <div className="space-y-2 text-xs text-slate-200">
          <label className="flex gap-2 items-start"><input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} className="mt-0.5 size-4" />{pl ? 'Potwierdzam ukończone 18 lat w oryginalnym wyniku/dokumencie.' : 'I confirmed age 18+ from the original result/document.'}</label>
          <label className="flex gap-2 items-start"><input type="checkbox" checked={present} onChange={(e) => setPresent(e.target.checked)} className="mt-0.5 size-4" />{pl ? 'Ta osoba jest obecna i odpowiada okazanemu dokumentowi.' : 'The person is present and matches the document.'}</label>
          <label className="flex gap-2 items-start"><input type="checkbox" checked={consented} onChange={(e) => setConsented(e.target.checked)} className="mt-0.5 size-4" />{pl ? 'Osoba zgodziła się na weryfikację i zna cel.' : 'The person consented to this check and understands its purpose.'}</label>
          <label className="flex gap-2 items-start"><input type="checkbox" checked={bound} onChange={(e) => setBound(e.target.checked)} className="mt-0.5 size-4" />{pl ? 'Kod konta odczytano z zalogowanego CartMate tej osoby.' : 'I read the account code from this person’s signed-in CartMate.'}</label>
        </div>
        <button
          type="submit"
          disabled={busy || !subjectId.trim() || !accountChallenge.trim() || !adult || !present || !consented || !bound}
          className="w-full rounded-xl bg-sky-400 px-4 py-3 font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
        >
          {busy ? (pl ? 'Zapisywanie…' : 'Saving…') : (pl ? 'Zapisz potwierdzenie 18+' : 'Record 18+ check')}
        </button>
        {result && <p role="status" className="text-xs text-emerald-300">{result}</p>}
        {error && <p role="alert" className="text-xs text-rose-300">{error}</p>}
      </form>
    </section>
  );
}
