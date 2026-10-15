import React, { useState } from 'react';
import { Lock, AlertCircle, Sparkles, MapPin } from 'lucide-react';
import type { ActivityCategory, User, RendezvousSuggestion } from '../types';
import type { Language } from '../locales';
import { translations } from '../locales';
import { classifyIntent, screenContent, suggestRendezvous, POLISH_CITIES } from '../api';
import { SILESIA_VENUES } from '../data/silesiaVenues';
import { ACTIVITIES } from '../constants/activities';
import { useDialogFocus } from '../hooks/useDialogFocus';

interface CreatePingModalProps {
  currentUser: User;
  lang: Language;
  onClose: () => void;
  onSubmit: (pingData: any) => Promise<void>;
  onNavigateSafety: () => void;
}

export const CreatePingModal: React.FC<CreatePingModalProps> = ({
  currentUser,
  lang,
  onClose,
  onSubmit,
  onNavigateSafety,
}) => {
  const t = translations[lang];
  const [destinationName, setDestinationName] = useState('');
  const [address, setAddress] = useState('');
  const [category, setCategory] = useState<ActivityCategory>('social');
  const [ttlMinutes, setTtlMinutes] = useState(45);
  const [notes, setNotes] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>(
    lang === 'pl' ? ['#ChwilaRazem'] : ['#ChillCompany']
  );
  const [womenOnly, setWomenOnly] = useState(currentUser.is_id_verified && currentUser.safe_haven_enabled);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [safetyError, setSafetyError] = useState<string | null>(null);
  const [isAnalyzingJev, setIsAnalyzingJev] = useState(false);
  const [suggestedSpots, setSuggestedSpots] = useState<RendezvousSuggestion[]>([]);

  useDialogFocus('create-ping-dialog', true, onClose);

  const storePresets = SILESIA_VENUES;

  const availableTags = lang === 'pl' ? [
    '#ChwilaRazem', '#WspólnySpacer', '#WspólnaNauka', '#RazemNaTrening', '#PosiłekRazem',
    '#NocneGastro',
    '#BurgerKingRun',
    '#NieChcęJeśćSam',
    '#RozmowaPrzyFrytkach',
    '#PracaZLaptopem',
    '#PromocjaWielosztuki',
    '#KartaMakroVIP',
    '#DzieleniePaczki5050',
    '#DrugaOpiniaNaZakupach',
    '#SpokojneZakupy',
    '#PomocWZnoszeniu',
    '#KawaPoZakupach',
    '#KlopsikiIkea',
  ] : lang === 'uk' ? [
    '#РазомНаПрогулянку', '#НавчанняРазом', '#РазомНаТренування', '#Поговоримо',
    '#НічнийПерекус',
    '#BurgerKingКатовіце',
    '#НеХочуЇстиСам',
    '#РозмоваЗаФрі',
    '#РоботаЗНоутбуком',
    '#Знижки5050',
    '#СпільніПокупки',
    '#КаваТаСпілкування',
    '#BiedronkaАкції',
    '#СпокійніПокупки',
    '#ДопомогаЗРечами',
  ] : lang === 'ru' ? [
    '#ПрогулкаВместе', '#УчимсяВместе', '#ТренировкаВместе', '#Поговорим',
    '#НочнойПерекус',
    '#BurgerKingКатовице',
    '#НеХочуЕстьОдин',
    '#РазговорЗаЕдой',
    '#КоворкингСНоутом',
    '#Скидки5050',
    '#СовместныеПокупки',
    '#КофеИОбщение',
    '#АкцииBiedronka',
    '#СпокойныеПокупки',
    '#ПомощьСВещами',
  ] : [
    '#WalkTogether', '#StudyTogether', '#TrainTogether', '#TalkTogether', '#MealTogether',
    '#LateNightBites',
    '#BurgerKingRun',
    '#DontWannaEatAlone',
    '#FriesAndTalk',
    '#LaptopCoWork',
    '#SplittingBulk',
    '#ExecutiveMemberPass',
    '#SeasonalSnacksScout',
    '#NeedStylingAdvice',
    '#ChillCompany',
    '#TwoCartRun',
    '#QuickCoffeeFirst',
  ];

  const handleSelectPreset = (preset: typeof storePresets[number]) => {
    setDestinationName(preset.name);
    setAddress(preset.address);
    setCategory(preset.category);
  };

  const toggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter((t) => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  const handleRunJevAI = async () => {
    const textToAnalyze = notes.trim() || destinationName.trim();
    if (!textToAnalyze) return;
    setIsAnalyzingJev(true);
    setSafetyError(null);
    try {
      const [intentResult, safetyResult, spotResults] = await Promise.all([
        classifyIntent(textToAnalyze, category),
        screenContent(notes || destinationName),
        destinationName.trim() ? suggestRendezvous(destinationName.trim(), category) : Promise.resolve([]),
      ]);

      if (!safetyResult.is_safe) {
        setSafetyError(safetyResult.flagged_reasons.join(' ') || 'Treść zawiera słowa niezgodne z zasadami społeczności.');
      } else {
        setSafetyError(null);
      }

      if (intentResult.intent_tags && intentResult.intent_tags.length > 0) {
        setSelectedTags((prev) => Array.from(new Set([...prev, ...intentResult.intent_tags])));
      }
      // Classification is advisory. Keep the activity the person explicitly chose.
      if (spotResults && spotResults.length > 0) {
        setSuggestedSpots(spotResults);
      }
    } catch (e) {
      console.warn('Jev AI assist error:', e);
    } finally {
      setIsAnalyzingJev(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destinationName.trim() || !address.trim()) {
      alert(lang === 'pl' ? 'Wpisz publiczne miejsce spotkania i adres.' : 'Please enter a public meeting place and address.');
      return;
    }

    const matchedVenue = storePresets.find(
      (venue) => venue.name === destinationName.trim() && venue.address === address.trim()
    );
    const cityCenter = POLISH_CITIES.find((city) => city.name === currentUser.city);
    if (!matchedVenue && !cityCenter) {
      setSafetyError(lang === 'pl' ? 'Nie znamy jeszcze położenia tego miasta. Wybierz publiczny punkt z listy.' : 'This city has no map location yet. Choose a public venue from the list.');
      return;
    }

    setSafetyError(null);
    if (notes.trim()) {
      try {
        const safety = await screenContent(notes.trim());
        if (!safety.is_safe) {
          setSafetyError(
            safety.flagged_reasons.join(' ') ||
            (lang === 'pl'
              ? 'Wpisana treść narusza zasady bezpieczeństwa CartMate.'
              : 'Content violates CartMate safety guidelines.')
          );
          return;
        }
      } catch (e) {
        console.warn('Safety check skipped:', e);
      }
    }

    setIsSubmitting(true);
    try {
      await onSubmit({
        category,
        destination_name: destinationName,
        destination_lat: matchedVenue?.lat ?? cityCenter!.lat,
        destination_lng: matchedVenue?.lng ?? cityCenter!.lng,
        address,
        intent_tags: selectedTags,
        ttl_minutes: ttlMinutes,
        notes,
        women_only: womenOnly,
      });
      onClose();
    } catch (err: any) {
      alert(err.message || 'Błąd zapisu wyjścia');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      id="create-ping-dialog"
      className="app-dialog fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center p-3 sm:p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-ping-title"
      tabIndex={-1}
    >
      <div className="bg-[#0f172a] border border-slate-700 w-full max-w-md rounded-2xl p-4 sm:p-5 space-y-4 shadow-2xl my-auto">
        <div className="flex items-start justify-between">
          <div>
            <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">
              {t.postPingTitle}
            </span>
            <h3 id="create-ping-title" className="text-lg font-bold text-white tracking-tight">{t.broadcastSub}</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Zamknij"
            className="flex min-h-10 min-w-10 items-center justify-center text-slate-400 hover:text-white text-lg font-bold cursor-pointer"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <p className="rounded-xl border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs leading-relaxed text-blue-100">
            {t.postOrdinaryDisclosure}
          </p>
          {/* Orientation points only; users must confirm public access and hours. */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">{t.storePresetsLabel}</label>
            <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
              {storePresets.map((preset) => (
                <button
                  type="button"
                  key={preset.name}
                  onClick={() => handleSelectPreset(preset)}
                  className="shrink-0 text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/80 cursor-pointer"
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>

          {/* Public meeting point and address */}
          <div className="space-y-2">
            <div>
              <label htmlFor="create-ping-destination" className="text-xs font-medium text-slate-400 block mb-1">{t.destNameLabel}</label>
              <input
                id="create-ping-destination"
                type="text"
                required
                value={destinationName}
                onChange={(e) => setDestinationName(e.target.value)}
                placeholder={lang === 'pl' ? 'np. Biblioteka Śląska, wejście główne' : 'e.g. public library main entrance'}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label htmlFor="create-ping-address" className="text-xs font-medium text-slate-400 block mb-1">{t.addressLabel}</label>
              <input
                id="create-ping-address"
                type="text"
                required
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="np. ul. Mariacka 2, Katowice"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <p className="mt-1 text-[10px] text-slate-400">
                {lang === 'pl'
                  ? 'Dla własnego adresu mapa pokazuje tylko przybliżone centrum miasta. Ustalcie publiczne wejście w planie.'
                  : 'For a custom address, the map shows only the approximate city center. Agree on a public entrance in the plan.'}
              </p>
            </div>
          </div>

          {/* Activity Category */}
          <div>
            <label htmlFor="create-ping-category" className="text-xs font-medium text-slate-400 block mb-1">{t.categoryLabel}</label>
            <select
              id="create-ping-category"
              value={category}
              onChange={(e) => setCategory(e.target.value as ActivityCategory)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
            >
              {ACTIVITIES.map((activity) => (
                <option key={activity.id} value={activity.id}>{t[activity.labelKey]}</option>
              ))}
            </select>
            <p className="mt-1.5 text-[11px] leading-relaxed text-slate-400">
              {t.activityVenueHint}
            </p>
          </div>

          {/* Time-To-Live (TTL) Decay */}
          <div>
            <label className="text-xs font-medium text-slate-400 flex items-center justify-between mb-1.5">
              <span>{t.lifespanLabel}</span>
              <span className="text-emerald-400 font-bold">{ttlMinutes} {lang === 'pl' ? 'minut' : 'minutes'}</span>
            </label>
            <div className="flex gap-2">
              {[30, 45, 60, 90].map((min) => (
                <button
                  type="button"
                  key={min}
                  onClick={() => setTtlMinutes(min)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer border ${
                    ttlMinutes === min
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/60'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  {min}m
                </button>
              ))}
            </div>
          </div>

          {/* Intent Tag Chips */}
          <div>
            <label className="text-xs font-medium text-slate-400 block mb-1.5">{t.intentTagsLabel}</label>
            <div className="flex flex-wrap gap-1.5">
              {availableTags.map((tag) => {
                const isSelected = selectedTags.includes(tag);
                return (
                  <button
                    type="button"
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className={`text-[11px] px-2 py-1 rounded-lg border transition cursor-pointer ${
                      isSelected
                        ? 'bg-teal-500/20 text-teal-300 border-teal-500/50 font-semibold'
                        : 'bg-slate-900 text-slate-400 border-slate-800'
                    }`}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Women-Only SafeHaven Toggle */}
          {currentUser.gender === 'female' && (
            <div className="bg-purple-950/20 border border-purple-500/30 p-3 rounded-xl flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-purple-400" />
                  <span className="text-xs font-bold text-purple-200">{t.safeHavenToggleTitle}</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  {currentUser.is_id_verified ? t.safeHavenToggleDesc : t.idRequiredDesc}
                </p>
              </div>
              <input
                type="checkbox"
                checked={womenOnly}
                onChange={(e) => setWomenOnly(e.target.checked)}
                disabled={!currentUser.is_id_verified}
                aria-label={t.safeHavenToggleTitle}
                className="w-4 h-4 accent-purple-500 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
              />
            </div>
          )}
          {currentUser.gender === 'female' && !currentUser.is_id_verified && (
            <button
              type="button"
              onClick={() => {
                onClose();
                onNavigateSafety();
              }}
              className="text-xs font-semibold text-purple-300 underline underline-offset-2"
            >
              {t.verifyQuickBtn}
            </button>
          )}

          {/* Personal Note & Jev AI Assist */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label htmlFor="create-ping-notes" className="text-xs font-medium text-slate-400 block">{t.companionNotesLabel}</label>
              <button
                type="button"
                onClick={handleRunJevAI}
                disabled={isAnalyzingJev || (!notes.trim() && !destinationName.trim())}
                className="text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition disabled:opacity-40 cursor-pointer"
              >
                <Sparkles className={`w-3 h-3 ${isAnalyzingJev ? 'animate-spin' : ''}`} />
                <span>{isAnalyzingJev ? 'Analiza Jev AI...' : 'Jev AI: Dopasuj tagi i punkty'}</span>
              </button>
            </div>
            <textarea
              id="create-ping-notes"
              rows={2}
              value={notes}
              onChange={(e) => {
                setNotes(e.target.value);
                if (safetyError) setSafetyError(null);
              }}
              placeholder={t.notesPlaceholder}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Safety Error Alert */}
          {safetyError && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-2 animate-shake">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-bold block">Blokada bezpieczeństwa treści:</span>
                <p className="text-[11px] text-rose-200">{safetyError}</p>
              </div>
            </div>
          )}

          {/* Jev Rendezvous Suggestions */}
          {suggestedSpots.length > 0 && (
            <div className="space-y-2 p-3 bg-slate-900/80 border border-emerald-500/30 rounded-xl">
              <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-bold">
                <MapPin className="w-3.5 h-3.5" />
                <span>{lang === 'pl' ? 'Propozycje publicznych punktów spotkania (niezweryfikowane)' : 'Suggested public meeting points (not verified)'}</span>
              </div>
              <div className="space-y-1.5">
                {suggestedSpots.map((spot, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-left space-y-0.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-200">{spot.title}</span>
                      <span className="text-[10px] text-emerald-400 font-medium">{spot.safety_rating}</span>
                    </div>
                    <p className="text-[11px] text-slate-400">{spot.description}</p>
                    <p className="text-[10px] text-slate-500 italic">💡 {spot.tip}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Submit */}
          <div className="pt-2 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl border border-slate-700 text-slate-300 text-xs font-bold hover:bg-slate-800 transition cursor-pointer"
            >
              {t.cancel}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-lg shadow-emerald-500/20 transition cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? t.publishing : t.publishToRadar}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
