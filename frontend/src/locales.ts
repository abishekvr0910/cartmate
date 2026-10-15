export type Language = 'pl' | 'en' | 'uk' | 'ru';

export interface TranslationDictionary {
  appName: string;
  locationDefault: string;
  radiusDefault: string;
  radarTitle: string;
  radarDesc: string;
  postRunBtn: string;
  safeHavenFilter: string;
  safeHavenSub: string;
  allPings: string;
  catStudy: string;
  catFitness: string;
  catWalk: string;
  catFood: string;
  catSocial: string;
  catQuick: string;
  catGrocery: string;
  catWholesale: string;
  catFashion: string;
  catHome: string;
  catLateNight: string;
  catCafe: string;
  catEntertainment: string;
  noPings: string;
  firstToPost: string;
  minutesLeft: string;
  away: string;
  joinRun: string;
  requests: string;
  requestModalTitle: string;
  quickNoteLabel: string;
  safetyTipTitle: string;
  safetyTipText: string;
  cancel: string;
  sendRequest: string;
  sending: string;
  sent: string;
  reviewApplicants: string;
  noApplicantsYet: string;
  acceptCompanion: string;
  
  // Create Ping
  postPingTitle: string;
  broadcastSub: string;
  storePresetsLabel: string;
  destNameLabel: string;
  addressLabel: string;
  categoryLabel: string;
  activityVenueHint: string;
  noExpectedSpend: string;
  mutualConnectionsTitle: string;
  mutualConnectionsDesc: string;
  mutualConnectionsEmpty: string;
  sharedOutings: string;
  mutualContact: string;
  meetAgainPrompt: string;
  mutualConfirmed: string;
  noLongerNeeded: string;
  planWhenLabel: string;
  planMeetingPointLabel: string;
  planMeetingPointHint: string;
  lifespanLabel: string;
  intentTagsLabel: string;
  safeHavenToggleTitle: string;
  safeHavenToggleDesc: string;
  companionNotesLabel: string;
  notesPlaceholder: string;
  publishToRadar: string;
  publishing: string;
  idRequiredTitle: string;
  idRequiredDesc: string;
  postOrdinaryDisclosure: string;
  verifyQuickBtn: string;

  // Safety Hub
  safetyHubTitle: string;
  safetyHubDesc: string;
  yourTier: string;
  tierBronzeTitle: string;
  tierBronzeDesc: string;
  tierBronzeUnconfirmedTitle: string;
  tierBronzeUnconfirmedDesc: string;
  tierSilverTitle: string;
  tierSilverDesc: string;
  tierSilverBtn: string;
  tierSilverSuccess: string;
  tierGoldTitle: string;
  tierGoldDesc: string;
  emergencyContactTitle: string;
  emergencyContactDesc: string;
  activeBadge: string;
  promiseTitle: string;
  promise1: string;
  promise2: string;
  promise3: string;

  // Active Trip
  noActiveTripTitle: string;
  noActiveTripDesc: string;
  tripCancelledNotice: string;
  dismissNotice: string;
  exploreRadarBtn: string;
  tripStatus: string;
  statusAwaiting: string;
  statusShopping: string;
  statusSos: string;
  sosBtn: string;
  designatedDest: string;
  rendezvousLabel: string;
  checkinStatusLabel: string;
  checkinBoth: string;
  checkinYou: string;
  checkinWaiting: string;
  arrivedBtn: string;
  companionHeader: string;
  chatHeader: string;
  chatPlaceholder: string;
  finishOutingBtn: string;
  sosModalTitle: string;
  sosModalDesc: string;
  sosConfirmBtn: string;
  sosConsentLabel: string;
  sosOpeningLabel: string;
  sosFallbackNoDispatch: string;
  sosFooter: string;
  sosDelivered: string;
  sosDispatched: string;
  completedOutingTitle: string;
  completedOutingDesc: string;
  submitReviewBtn: string;
  finishWithoutReviewBtn: string;
  meetAgainOptional: string;
  outingCommentLabel: string;
  followUpSaveFailed: string;

  // Profile
  sharedTrips: string;
  ratingLabel: string;
  offlineHours: string;
  viewCredentials: string;
  testPersonasTitle: string;
  testPersonasDesc: string;
  impactTitle: string;
  impactTrips: string;
  impactHours: string;
  impactSavings: string;
  impactSafety: string;
  currency: string;

  // Nav
  tabRadar: string;
  tabNearby: string;
  tabSafety: string;
  tabPost: string;
  tabTrip: string;
  newChatMessage: string;
  tabProfile: string;

  // Living Community & Low-Friction Connection
  peopleNearby: string;
  peopleShoppingNearby: string;
  privacyBannerText: string;
  actionWave: string;
  actionJoin: string;
  actionAsk: string;
  wavedSuccess: string;
  intentAll: string;

  // Spot Voting & Demand Pooling
  spotVotingTitle: string;
  spotVotingSub: string;
  spotVoteBtn: string;
  spotVotedBtn: string;
  spotGroupFormed: string;
  spotJoinCrew: string;
  suggestSpotBtn: string;
  suggestModalTitle: string;

  // Auth & Navigation Enhancements
  authTitleLogin: string;
  authTitleRegister: string;
  authTabLogin: string;
  authTabRegister: string;
  authIdentifierLabel: string;
  authIdentifierPlaceholder: string;
  authCodeLabel: string;
  authDemoQuickLogin: string;
  authLoginBtn: string;
  authRegisterBtn: string;
  authFullName: string;
  authGender: string;
  authCity: string;
  authBio: string;
  authLoggingIn: string;
  authRegistering: string;
  logoutBtn: string;
  switchAccountBtn: string;
  citySelectTitle: string;
  radarMapTitle: string;
  radarMapSub: string;

  // Innovations (Karrot, Daangn, Spliit)
  mannerTempTitle: string;
  mannerTempSub: string;
  mannerBadgeWarm: string;
  mannerBadgesPunctual: string;
  mannerBadgesPolite: string;
  mannerBadgesQuickSplit: string;
  mannerBadgesHelpful: string;
  pinHandshakeTitle: string;
  pinHandshakeDesc: string;
  yourPinLabel: string;
  enterCompanionPin: string;
  verifyPinBtn: string;
  pinVerifiedBadge: string;
  splitTabTitle: string;
  splitTabDesc: string;
  addItemSplitBtn: string;
  itemNameLabel: string;
  itemPriceLabel: string;
  payerLabel: string;
  split5050: string;
  hostOwes: string;
  companionOwes: string;
  settleBlikBtn: string;
  blikCopied: string;
  noItemsSplit: string;
  safetyTimerTitle: string;
  safetyTimerDesc: string;
  safetyTimeRemaining: string;

  // Social Proof & Social Media Connection
  socialProofTitle: string;
  socialProofSub: string;
  socialConnectBtn: string;
  socialDisconnectBtn: string;
  socialVerifiedBadge: string;
  socialInstagram: string;
  socialLinkedIn: string;
  socialTikTok: string;
  socialFacebook: string;
  socialModalTitle: string;
  socialModalDesc: string;
  socialHandleLabel: string;
  socialHandlePlaceholder: string;
  socialConfirmConnect: string;
  socialSharePing: string;
  socialShareSuccess: string;

  // Instagram & Dating App Look-alike features
  storiesTitle: string;
  yourStory: string;
  viewModeFeed: string;
  viewModeDeck: string;
  viewModeMap: string;
  vibeMatch: string;
  deckNext: string;
  deckMatch: string;
  deckSuperPing: string;
  whyGoing: string;
  idealCompanion: string;
  likedTooltip: string;
  bookmarkedTooltip: string;
  itsAnOuting: string;
  celebrateSub: string;
  openChatCoord: string;
}

export const translations: Record<Language, TranslationDictionary> = {
  pl: {
    appName: "CartMate",
    locationDefault: "Katowice, centrum",
    radiusDefault: "promień 8 km",
    radarTitle: "Znajdź towarzystwo na dziś",
    radarDesc: "Spacer, nauka, trening, jedzenie lub zwykła sprawa — wybierz towarzystwo i uzgodnijcie publiczne miejsce spotkania.",
    postRunBtn: "+ Dodaj Wyjście",
    safeHavenFilter: "Strefa Kobiet",
    safeHavenSub: "(Wyjścia wyłącznie dla kobiet)",
    allPings: "Wszystkie Wyjścia",
    catStudy: "📚 Wspólna nauka",
    catFitness: "🏃 Trening / ruch",
    catWalk: "🚶 Spacer",
    catFood: "🍽️ Wspólny posiłek",
    catSocial: "💬 Rozmowa / towarzystwo",
    catQuick: "⚡ Sprawy do załatwienia",
    catGrocery: "🥦 Biedronka / Lidl / Spożywcze",
    catWholesale: "📦 Makro / Selgros (Hurt)",
    catFashion: "🛍️ Silesia City Center / Galerie",
    catHome: "🛋️ IKEA Katowice / Dom",
    catLateNight: "🍔 Burger King & Nocne Gastro",
    catCafe: "☕ Kawa & Co-working",
    catEntertainment: "🍿 Kino / Miasto / Spacery",
    noPings: "Brak aktywnych wyjść w wybranej kategorii.",
    firstToPost: "Bądź pierwszą osobą, która doda wyjście!",
    minutesLeft: "zostało",
    away: "od Ciebie",
    joinRun: "Poproś o dołączenie",
    requests: "Zgłoszenia",
    requestModalTitle: "Dołącz do wspólnego wyjścia",
    quickNoteLabel: "Szybka wiadomość do gospodarza:",
    safetyTipTitle: "Zasada Bezpieczeństwa:",
    safetyTipText: "Wybierzcie konkretny, publiczny i łatwy do znalezienia punkt spotkania. Nie podawaj prywatnego adresu; sprawdź dostęp i koszty miejsca.",
    cancel: "Anuluj",
    sendRequest: "Wyślij Zgłoszenie",
    sending: "Wysyłanie...",
    sent: "Wysłano!",
    reviewApplicants: "Zgłoszenia do wyjścia",
    noApplicantsYet: "Brak zgłoszeń. Twoje wyjście jest widoczne na radarze!",
    acceptCompanion: "Zaakceptuj towarzysza i otwórz zbiórkę",
    
    // Create Ping
    postPingTitle: "Zaproś kogoś na wspólne wyjście",
    broadcastSub: "Widoczne dla sąsiadów w promieniu kilku kilometrów",
    storePresetsLabel: "Publiczne miejsca na Śląsku:",
    destNameLabel: "Publiczne miejsce spotkania",
    addressLabel: "Adres / Ulica",
    categoryLabel: "Kategoria Wyjścia",
    activityVenueHint: "Wybierz publiczne, łatwe do znalezienia miejsce. Sprawdźcie godziny i dostęp; siłownia może wymagać karnetu. Ustalcie czas oraz koszty w planie przed spotkaniem.",
    noExpectedSpend: "Bez planowanych wydatków",
    mutualConnectionsTitle: "Osoby, z którymi spotkasz się ponownie",
    mutualConnectionsDesc: "Oboje wyraziliście chęć kolejnego wspólnego wyjścia. To nie jest zgoda na kontakt poza CartMate.",
    mutualConnectionsEmpty: "Po wspólnym wyjściu możecie oboje zdecydować, czy chcecie spotkać się ponownie. Bez presji.",
    sharedOutings: "wspólnych wyjść",
    mutualContact: "Wzajemna zgoda",
    meetAgainPrompt: "Czy chcesz kiedyś ponownie spotkać się z",
    mutualConfirmed: "Oboje chcecie spotkać się ponownie. Znajdziesz tę osobę w profilu.",
    noLongerNeeded: "To wyjście nie jest już potrzebne",
    planWhenLabel: "Data i godzina",
    planMeetingPointLabel: "Dokładny publiczny punkt spotkania",
    planMeetingPointHint: "Podaj wejście, plac lub inny rozpoznawalny punkt; nie prywatny adres. Ustalcie go razem przed akceptacją.",
    lifespanLabel: "Czas ważności wpisu (zniknie po):",
    intentTagsLabel: "Tagi intencji i celu:",
    safeHavenToggleTitle: "Włącz Strefę Kobiet (SafeHaven)",
    safeHavenToggleDesc: "Tylko zweryfikowane kobiety zobaczą to wyjście",
    companionNotesLabel: "Dodatkowa notatka dla towarzysza",
    notesPlaceholder: "np. Chcę pouczyć się godzinę w bibliotece. Spotkajmy się przy głównym wejściu.",
    publishToRadar: "🚀 Opublikuj na Radarze",
    publishing: "Publikowanie...",
    idRequiredTitle: "Wymagana Weryfikacja Tożsamości",
    idRequiredDesc: "Wyjścia tylko dla kobiet wymagają weryfikacji tożsamości. Ta funkcja nie jest jeszcze dostępna.",
    postOrdinaryDisclosure: "Prywatny pilotaż: tylko zaproszone osoby 18+ po zatwierdzonej weryfikacji wieku. Dostęp może pochodzić z SMS lub przyjęcia przez operatora; żadna z tych metod sama nie potwierdza wieku. Uzgodnijcie publiczny punkt, czas i ewentualne koszty przed spotkaniem.",
    verifyQuickBtn: "Zobacz status weryfikacji",

    // Safety Hub
    safetyHubTitle: "Centrum Zaufania i Bezpieczeństwa",
    safetyHubDesc: "Narzędzia bezpieczeństwa CartMate. Weryfikacja tożsamości i kontaktu alarmowego nie jest jeszcze dostępna.",
    yourTier: "Twój Poziom Weryfikacji:",
    tierBronzeTitle: "Poziom 1: Brązowy (potwierdzony numer SMS)",
    tierBronzeDesc: "SMS potwierdza wyłącznie numer telefonu. Publikacja wyjść wymaga też zatwierdzonej weryfikacji wieku 18+, która nie jest jeszcze dostępna.",
    tierBronzeUnconfirmedTitle: "Numer telefonu niepotwierdzony",
    tierBronzeUnconfirmedDesc: "Potwierdzenie SMS nie wystarcza do publikacji. Potrzebna jest też zatwierdzona weryfikacja wieku 18+; konto demonstracyjne jej nie zapewnia.",
    tierSilverTitle: "Poziom 2: Srebrny (weryfikacja dokumentu — niedostępna)",
    tierSilverDesc: "Docelowa weryfikacja wymaga zewnętrznego dostawcy. Obecnie nie jest dostępna.",
    tierSilverBtn: "✨ Zweryfikuj Tożsamość (Symulacja)",
    tierSilverSuccess: "Zweryfikowano pomyślnie! Awansowano do Poziomu Srebrnego.",
    tierGoldTitle: "Poziom 3: Złoty (Lider Społeczności)",
    tierGoldDesc: "Poziom planowany; niezależne sprawdzenie przeszłości nie jest obecnie dostępne.",
    emergencyContactTitle: "Zaufany Kontakt Alarmowy",
    emergencyContactDesc: "Kontakt alarmowy nie jest jeszcze konfigurowany ani potwierdzany. W nagłym zagrożeniu zadzwoń pod 112.",
    activeBadge: "Aktywny",
    promiseTitle: "Standard Odpowiedzialnej Aplikacji",
    promise1: "Zero Inwazyjnych Reklam: Nie sprzedajemy Twojej uwagi ani nie profilujemy Cię pod reklamy.",
    promise2: "Brak Śledzenia Kontaktów: Nigdy nie pobieramy kontaktów z Twojego telefonu.",
    promise3: "Prawdziwe Życie: Aplikacja ma pomóc szybko znaleźć towarzysza, a potem schować telefon do kieszeni.",

    // Active Trip
    noActiveTripTitle: "Brak Aktywnego Wyjścia",
    noActiveTripDesc: "Dołącz do wyjścia na radarze lub zaakceptuj zgłoszenie, aby rozpocząć wspólne wyjście.",
    tripCancelledNotice: "Wyjście zostało anulowane. Nie jedź na miejsce spotkania; możesz poszukać innego planu.",
    dismissNotice: "Zamknij powiadomienie",
    exploreRadarBtn: "Przeglądaj Radar",
    tripStatus: "Status Wyjścia",
    statusAwaiting: "Oczekiwanie na zbiórkę przy wejściu",
    statusShopping: "Wspólne wyjście w toku",
    statusSos: "🚨 OPCJE POMOCY OTWARTE",
    sosBtn: "SOS",
    designatedDest: "Docelowe Miejsce Spotkania",
    rendezvousLabel: "Miejsce Zbiórki:",
    checkinStatusLabel: "Status obecności:",
    checkinBoth: "Oboje obecni na miejscu",
    checkinYou: "Jesteś na miejscu • Czekasz na towarzysza",
    checkinWaiting: "Kliknij po dotarciu pod wejście",
    arrivedBtn: "📍 Jestem na miejscu",
    companionHeader: "Twój Towarzysz",
    chatHeader: "Czat Wyjścia i Koordynacja",
    chatPlaceholder: "Napisz np. 'Stoję przy wejściu w czarnej kurtce'...",
    finishOutingBtn: "Zakończ wyjście",
    sosModalTitle: "Otworzyć opcje pomocy?",
    sosModalDesc: "CartMate nie dzwoni pod 112 ani nie wysyła SMS do kontaktu alarmowego. W bezpośrednim zagrożeniu samodzielnie zadzwoń pod 112.",
    sosConfirmBtn: "Pokaż opcje pomocy",
    sosConsentLabel: "Rozumiem, że CartMate nikogo nie powiadomi. Jeśli grozi mi niebezpieczeństwo, samodzielnie zadzwonię pod 112.",
    sosOpeningLabel: "Otwieranie...",
    sosFallbackNoDispatch: "Nikt nie został powiadomiony przez CartMate. Zadzwoń samodzielnie pod 112.",
    sosFooter: "CartMate nie zastępuje służb ratunkowych ani połączenia z numerem 112.",
    sosDelivered: "Operator potwierdził doręczenie powiadomienia do kontaktu alarmowego.",
    sosDispatched: "Powiadomienie przekazano dostawcy; doręczenie nie jest potwierdzone.",
    completedOutingTitle: "Zakończ wyjście",
    completedOutingDesc: "Ocena jest opcjonalna. Jak oceniasz wspólne wyjście z towarzyszem?",
    submitReviewBtn: "Zapisz ocenę i zakończ wyjście",
    finishWithoutReviewBtn: "Zakończ bez oceny",
    meetAgainOptional: "Opcjonalne. Żadna odpowiedź nie jest zaznaczona domyślnie; tylko dwa świadome „Tak” tworzą połączenie.",
    outingCommentLabel: "Komentarz o wyjściu",
    followUpSaveFailed: "Wyjście zakończono, ale nie udało się zapisać odpowiedzi o ponownym spotkaniu.",

    // Profile
    sharedTrips: "Wspólne Wyjścia",
    ratingLabel: "Średnia Ocen",
    offlineHours: "Ukończone wyjścia",
    viewCredentials: "Zobacz Certyfikaty i Odznaki",
    testPersonasTitle: "Interaktywne Profile Testowe",
    testPersonasDesc: "Przełącz się między rolami, aby przetestować aplikację z perspektywy różnych użytkowników:",
    impactTitle: "Wpływ Społeczności CartMate w Polsce",
    impactTrips: "Ukończone wyjścia",
    impactHours: "—",
    impactSavings: "—",
    impactSafety: "Brak zweryfikowanych danych",
    currency: "zł",

    // Nav
    tabRadar: "W pobliżu",
    tabNearby: "W pobliżu",
    tabSafety: "Bezpieczeństwo",
    tabPost: "Dodaj Wyjście",
    tabTrip: "Aktywne Wyjście",
    newChatMessage: "Nowa wiadomość od osoby towarzyszącej",
    tabProfile: "Profil",

    // Living Community & Low-Friction Connection
    peopleNearby: "Ludzie w pobliżu",
    peopleShoppingNearby: "osób w Twojej okolicy planuje wyjście",
    privacyBannerText: "Przybliżona lokalizacja i publiczne miejsca spotkań — nie adres domu.",
    actionWave: "👋 Pomachaj",
    actionJoin: "🤝 Dołącz",
    actionAsk: "💬 Zapytaj",
    wavedSuccess: "Pomachano do sąsiada! 👋",
    intentAll: "Wszystkie",

    // Spot Voting & Demand Pooling
    spotVotingTitle: "Głosowanie na miejscówki w okolicy",
    spotVotingSub: "Zbierzmy ekipę! Gdy zbierze się min. 3 osoby, automatycznie formuje się wspólne wyjście.",
    spotVoteBtn: "Głosuj (+1)",
    spotVotedBtn: "Zagłosowano ✓",
    spotGroupFormed: "🔥 Ekipa gotowa do wyjścia!",
    spotJoinCrew: "Dołącz do ekipy",
    suggestSpotBtn: "+ Zaproponuj miejscówkę",
    suggestModalTitle: "Zaproponuj nową miejscówkę w okolicy",

    // Auth & Navigation Enhancements
    authTitleLogin: "Logowanie do CartMate",
    authTitleRegister: "Utwórz konto w CartMate",
    authTabLogin: "Zaloguj się",
    authTabRegister: "Zarejestruj się",
    authIdentifierLabel: "Numer telefonu",
    authIdentifierPlaceholder: "np. +48 601 234 567",
    authCodeLabel: "Kod weryfikacyjny SMS OTP",
    authDemoQuickLogin: "Błyskawiczne logowanie profilem demo:",
    authLoginBtn: "Zaloguj się bezpiecznie",
    authRegisterBtn: "Utwórz nowe konto",
    authFullName: "Imię i Nazwisko",
    authGender: "Płeć",
    authCity: "Miasto pilotażu na Śląsku",
    authBio: "Krótko o mnie (zainteresowania / styl wyjść)",
    authLoggingIn: "Logowanie...",
    authRegistering: "Rejestracja...",
    logoutBtn: "Wyloguj się",
    switchAccountBtn: "Zmień konto / Zaloguj",
    citySelectTitle: "Wybierz miasto pilotażu na Śląsku:",
    radarMapTitle: "Mapa wyjść i ludzi w okolicy",
    radarMapSub: "Dotknij punktu na mapie, aby zaznaczyć wyjście",

    // Innovations
    mannerTempTitle: "Temperatura Kultury (Manner)",
    mannerTempSub: "Wskaźnik na podstawie opinii uczestników; nie jest niezależną weryfikacją.",
    mannerBadgeWarm: "Ciepły Towarzysz 🔥",
    mannerBadgesPunctual: "Punktualność ⏰",
    mannerBadgesPolite: "Wysoka Kultura 🤝",
    mannerBadgesQuickSplit: "Przejrzysty podział kosztów ⚡",
    mannerBadgesHelpful: "Pomocny i Uprzejmy 🛒",
    pinHandshakeTitle: "Wspólny kod spotkania",
    pinHandshakeDesc: "PIN potwierdza, że obie osoby znają kod spotkania; aplikacja nie weryfikuje lokalizacji ani obecności.",
    yourPinLabel: "Twój kod PIN spotkania:",
    enterCompanionPin: "Wpisz 4-cyfrowy kod towarzysza:",
    verifyPinBtn: "Potwierdź Spotkanie",
    pinVerifiedBadge: "Wpisano zgodny PIN ✓",
    splitTabTitle: "Kalkulator podziału 50/50",
    splitTabDesc: "Zapisz kwotę i oblicz szacunkową połowę. Aplikacja nie weryfikuje paragonów ani nie obsługuje płatności.",
    addItemSplitBtn: "+ Dodaj produkt do podziału 50/50",
    itemNameLabel: "Nazwa produktu / pozycji",
    itemPriceLabel: "Cena całkowita (zł)",
    payerLabel: "Kto zapłacił przy kasie?",
    split5050: "Podział 50/50",
    hostOwes: "Gospodarz zwraca:",
    companionOwes: "Towarzysz zwraca:",
    settleBlikBtn: "Skopiuj numer kontaktowy",
    blikCopied: "Skopiowano numer kontaktowy. Płatność wykonaj w swojej aplikacji bankowej.",
    noItemsSplit: "Brak dodanych produktów. Dodaj pozycję z paragonu, aby podzielić rachunek!",
    safetyTimerTitle: "Plan bezpieczeństwa",
    safetyTimerDesc: "Automatyczny licznik i alarm do kontaktu nie są dostępne. Ustal plan zaufaną osobą i w nagłym zagrożeniu dzwoń pod 112.",
    safetyTimeRemaining: "Sugerowany czas na własny kontakt z bliską osobą:",

    // Social Proof
    socialProofTitle: "Linki do profili społecznościowych",
    socialProofSub: "Dodanie linku nie potwierdza tożsamości ani autentyczności profilu.",
    socialConnectBtn: "Połącz",
    socialDisconnectBtn: "Odłącz",
    socialVerifiedBadge: "Połączono",
    socialInstagram: "Instagram",
    socialLinkedIn: "LinkedIn",
    socialTikTok: "TikTok",
    socialFacebook: "Facebook",
    socialModalTitle: "Połącz profil społecznościowy",
    socialModalDesc: "Tryb demonstracyjny: wpisanie nazwy konta nie potwierdza tożsamości ani własności profilu.",
    socialHandleLabel: "Nazwa użytkownika lub link:",
    socialHandlePlaceholder: "np. @zuzanna.arch lub zuzanna-wisniewska",
    socialConfirmConnect: "Zapisz testowy identyfikator",
    socialSharePing: "Udostępnij Wyjście",
    socialShareSuccess: "Skopiowano link wyjścia na Instagram Stories / WhatsApp!",

    // Instagram & Dating App Look-alike features
    storiesTitle: "Sąsiedzi wychodzą",
    yourStory: "+ Twoje Wyjście",
    viewModeFeed: "Wyjścia",
    viewModeDeck: "Karty",
    viewModeMap: "Mapa",
    vibeMatch: "Zgodność Vibe'u",
    deckNext: "Pomiń",
    deckMatch: "Poproś o miejsce",
    deckSuperPing: "Super-Ping ⭐",
    whyGoing: "Dlaczego dziś wychodzę:",
    idealCompanion: "Szukam towarzysza, który:",
    likedTooltip: "Dodano do ulubionych! ❤️",
    bookmarkedTooltip: "Zapisano wyjście! 🔖",
    itsAnOuting: "Jest chęć na wspólne wyjście! 🎉",
    celebrateSub: "Ustalcie konkretną godzinę i koszty na czacie. Obie osoby muszą zaakceptować plan.",
    openChatCoord: "Otwórz Czat i Koordynację",
  },

  en: {
    appName: "CartMate",
    locationDefault: "Katowice, city center",
    radiusDefault: "8 km radius",
    radarTitle: "Live Outing Radar",
    radarDesc: "Walk, study, train, eat or run an errand together. Agree on a public meeting point and clear terms first.",
    postRunBtn: "+ Post Outing",
    safeHavenFilter: "SafeHaven Filter",
    safeHavenSub: "(Women-Only outings)",
    allPings: "All Outings",
    catStudy: "📚 Study together",
    catFitness: "🏃 Fitness / movement",
    catWalk: "🚶 Walk",
    catFood: "🍽️ Share a meal",
    catSocial: "💬 Conversation / company",
    catQuick: "⚡ Errands / quick tasks",
    catGrocery: "🥦 Grocery (Biedronka/Lidl)",
    catWholesale: "📦 Wholesale (Makro/Selgros)",
    catFashion: "🛍️ Malls & Fashion",
    catHome: "🛋️ Home & Furniture (IKEA)",
    catLateNight: "🍔 Burger King & Late-Night Bites",
    catCafe: "☕ Coffee & Co-working",
    catEntertainment: "🍿 Cinema / Hangouts",
    noPings: "No live outings match your filter.",
    firstToPost: "Be the first to post an outing!",
    minutesLeft: "left",
    away: "away",
    joinRun: "Join Outing",
    requests: "Requests",
    requestModalTitle: "Request Companion Outing",
    quickNoteLabel: "Quick Note to Host:",
    safetyTipTitle: "Safety Rule:",
    safetyTipText: "Meetings must take place at the public venue entrance. Never share private home addresses!",
    cancel: "Cancel",
    sendRequest: "Send Request",
    sending: "Sending...",
    sent: "Sent!",
    reviewApplicants: "Review Outing Applicants",
    noApplicantsYet: "No applicants yet. Your ping is live on the local radar!",
    acceptCompanion: "Accept Companion & Open Rendezvous",

    // Create Ping
    postPingTitle: "Invite someone to join you",
    broadcastSub: "Visible to nearby neighbors",
    storePresetsLabel: "Public venues in Silesia:",
    destNameLabel: "Public meeting place",
    addressLabel: "Address / Landmark",
    categoryLabel: "Category",
    activityVenueHint: "Choose an easy-to-find public place. Check hours and access; a gym may require membership. Agree on time and costs in the plan before meeting.",
    noExpectedSpend: "No spending planned",
    mutualConnectionsTitle: "People to meet again",
    mutualConnectionsDesc: "You both chose to meet again. This is not consent to contact outside CartMate.",
    mutualConnectionsEmpty: "After an outing, you can each decide whether you would meet again. No pressure.",
    sharedOutings: "shared outings",
    mutualContact: "Mutual choice",
    meetAgainPrompt: "Would you meet again with",
    mutualConfirmed: "You both want to meet again. This person is listed in your profile.",
    noLongerNeeded: "This outing is no longer needed",
    planWhenLabel: "Date and time",
    planMeetingPointLabel: "Exact public meeting point",
    planMeetingPointHint: "Name an entrance, square or other recognizable point, not a home address. Agree on it before accepting.",
    lifespanLabel: "Broadcast Lifespan (Auto-Expires):",
    intentTagsLabel: "Trip Intent Tags:",
    safeHavenToggleTitle: "SafeHaven Mode (Women-Only)",
    safeHavenToggleDesc: "Only verified female companions can view & join",
    companionNotesLabel: "Notes for Companion",
    notesPlaceholder: "e.g. Study for an hour at the library; meet at the main entrance.",
    publishToRadar: "🚀 Post to Radar",
    publishing: "Posting...",
    idRequiredTitle: "Identity Verification Required",
    idRequiredDesc: "Women-only outings require genuine identity verification. This feature is not available yet.",
    postOrdinaryDisclosure: "Private pilot: invited adults with approved 18+ checks only. Access may use SMS or operator admission; neither alone proves age. Agree on a public meeting point, time and any costs before meeting.",
    verifyQuickBtn: "View verification status",

    // Safety Hub
    safetyHubTitle: "Trust & Safety Hub",
    safetyHubDesc: "CartMate safety tools. Identity verification and emergency-contact setup are not available yet.",
    yourTier: "Your Verification Tier:",
    tierBronzeTitle: "Tier 1: Bronze (SMS-confirmed number)",
    tierBronzeDesc: "SMS confirms only a phone number. Posting also requires approved 18+ age assurance, which is not available yet.",
    tierBronzeUnconfirmedTitle: "Phone number not confirmed",
    tierBronzeUnconfirmedDesc: "SMS confirmation alone does not permit posting. Approved 18+ age assurance is also required; a demo account does not provide it.",
    tierSilverTitle: "Tier 2: Silver (ID verification unavailable)",
    tierSilverDesc: "Identity checks require a genuine external provider and are not available yet.",
    tierSilverBtn: "✨ Verify ID & Selfie (Simulate)",
    tierSilverSuccess: "Successfully verified! Upgraded to Silver Tier.",
    tierGoldTitle: "Tier 3: Gold (Community Leader)",
    tierGoldDesc: "Planned tier; independent background checks are not currently available.",
    emergencyContactTitle: "Trusted Emergency Contact",
    emergencyContactDesc: "Emergency contacts cannot yet be configured or consent-verified. Call 112 in an emergency.",
    activeBadge: "Active",
    promiseTitle: "The CartMate Privacy Promise",
    promise1: "No Behavioral Ads: We never sell your attention or auction your data.",
    promise2: "No Contact Harvesting: We never scrape your address book or shadow-profile friends.",
    promise3: "Real-World Outcome: Our goal is for you to get off the phone and enjoy shared real life.",

    // Active Trip
    noActiveTripTitle: "No Outing Currently Active",
    noActiveTripDesc: "Join a nearby live ping on the radar or accept an incoming request to start a shared companion run.",
    tripCancelledNotice: "The outing was cancelled. Do not travel to the meeting point; you can look for another plan.",
    dismissNotice: "Dismiss notice",
    exploreRadarBtn: "Explore Live Radar",
    tripStatus: "Trip Status",
    statusAwaiting: "Awaiting Public Rendezvous",
    statusShopping: "Shared Outing Active",
    statusSos: "🚨 HELP OPTIONS OPEN",
    sosBtn: "SOS",
    designatedDest: "Designated Destination",
    rendezvousLabel: "Public Meeting Rendezvous:",
    checkinStatusLabel: "Check-in status:",
    checkinBoth: "Both Checked In",
    checkinYou: "You Checked In • Waiting for companion",
    checkinWaiting: "Tap when at entrance",
    arrivedBtn: "📍 I Arrived",
    companionHeader: "Your Companion",
    chatHeader: "Direct Trip Chat",
    chatPlaceholder: "Send quick arrival update (e.g. 'Standing outside in black jacket')...",
    finishOutingBtn: "Finish outing",
    sosModalTitle: "Open emergency options?",
    sosModalDesc: "CartMate does not call 112 or text your emergency contact. If you are in immediate danger, call 112 yourself.",
    sosConfirmBtn: "Show help options",
    sosConsentLabel: "I understand CartMate will not notify anyone. If I am in danger, I will call 112 myself.",
    sosOpeningLabel: "Opening...",
    sosFallbackNoDispatch: "CartMate has not notified anyone. Call 112 yourself.",
    sosFooter: "CartMate does not replace emergency services or a call to 112.",
    sosDelivered: "The carrier confirmed delivery to the emergency contact.",
    sosDispatched: "The provider accepted the message; delivery is not confirmed.",
    completedOutingTitle: "Finish outing",
    completedOutingDesc: "A review is optional. How was your outing with your companion?",
    submitReviewBtn: "Submit review and finish outing",
    finishWithoutReviewBtn: "Finish without a review",
    meetAgainOptional: "Optional. No answer is selected by default; only two deliberate Yes answers create a connection.",
    outingCommentLabel: "Outing comment",
    followUpSaveFailed: "Outing completed, but the meet-again answer was not saved.",

    // Profile
    sharedTrips: "Shared Outings",
    ratingLabel: "Rating",
    offlineHours: "Completed Outings",
    viewCredentials: "View Verification Credentials",
    testPersonasTitle: "Interactive Test Personas",
    testPersonasDesc: "Switch profile to test host, companion, and safety flows:",
    impactTitle: "CartMate Community Impact in Poland",
    impactTrips: "Completed outings",
    impactHours: "—",
    impactSavings: "—",
    impactSafety: "No verified data",
    currency: "zł",

    // Nav
    tabRadar: "Nearby",
    tabNearby: "Nearby",
    tabSafety: "Safety",
    tabPost: "Post Ping",
    tabTrip: "Active Trip",
    newChatMessage: "New message from your companion",
    tabProfile: "Profile",

    // Living Community & Low-Friction Connection
    peopleNearby: "People nearby",
    peopleShoppingNearby: "people nearby planning an outing",
    privacyBannerText: "Approximate location and public meeting places — not home addresses.",
    actionWave: "👋 Wave",
    actionJoin: "🤝 Join me",
    actionAsk: "💬 Ask",
    wavedSuccess: "Waved at neighbor! 👋",
    intentAll: "All",

    // Spot Voting & Demand Pooling
    spotVotingTitle: "Vote on Tonight's Neighborhood Spots",
    spotVotingSub: "Crowdsource a group! When 3+ people vote, a spontaneous outing forms automatically.",
    spotVoteBtn: "Vote (+1)",
    spotVotedBtn: "Voted ✓",
    spotGroupFormed: "🔥 Group formed! Ready to roll!",
    spotJoinCrew: "Join the crew",
    suggestSpotBtn: "+ Suggest a spot",
    suggestModalTitle: "Suggest a new neighborhood spot",

    // Auth & Navigation Enhancements
    authTitleLogin: "Sign in to CartMate",
    authTitleRegister: "Create CartMate Account",
    authTabLogin: "Log In",
    authTabRegister: "Register",
    authIdentifierLabel: "Phone Number",
    authIdentifierPlaceholder: "e.g. +48 601 234 567",
    authCodeLabel: "SMS OTP verification code",
    authDemoQuickLogin: "Instant demo account sign-in:",
    authLoginBtn: "Sign In Securely",
    authRegisterBtn: "Create New Account",
    authFullName: "Full Name",
    authGender: "Gender",
    authCity: "Silesia pilot city",
    authBio: "Short Bio (interests / outing style)",
    authLoggingIn: "Signing in...",
    authRegistering: "Registering...",
    logoutBtn: "Log Out",
    switchAccountBtn: "Switch Account / Login",
    citySelectTitle: "Select a Silesia pilot city:",
    radarMapTitle: "Nearby outings and people map",
    radarMapSub: "Tap any pin on the radar map to view companion outing",

    // Innovations (Karrot, Daangn, Spliit)
    mannerTempTitle: "Manner Temperature",
    mannerTempSub: "A score based on participant reviews; it is not independent verification.",
    mannerBadgeWarm: "Warm Companion 🔥",
    mannerBadgesPunctual: "Punctual ⏰",
    mannerBadgesPolite: "Courteous 🤝",
    mannerBadgesQuickSplit: "Clear cost sharing ⚡",
    mannerBadgesHelpful: "Helpful with Cart 🛒",
    pinHandshakeTitle: "Shared meeting PIN",
    pinHandshakeDesc: "The PIN confirms both people know the meeting code; the app does not verify location or physical presence.",
    yourPinLabel: "Your Rendezvous PIN:",
    enterCompanionPin: "Enter Companion's 4-Digit PIN:",
    verifyPinBtn: "Confirm Handshake",
    pinVerifiedBadge: "Matching PIN entered ✓",
    splitTabTitle: "50/50 cost calculator",
    splitTabDesc: "Record an amount and calculate an estimated half. The app does not verify receipts or process payments.",
    addItemSplitBtn: "+ Add Item to Split 50/50",
    itemNameLabel: "Item / Food Order Name",
    itemPriceLabel: "Total Cost (PLN)",
    payerLabel: "Who paid at checkout?",
    split5050: "50/50 Split",
    hostOwes: "Host reimburses:",
    companionOwes: "Companion reimburses:",
    settleBlikBtn: "Copy contact number",
    blikCopied: "Contact number copied. Complete any payment in your own banking app.",
    noItemsSplit: "No items added yet. Add a burger or grocery item to split the bill!",
    safetyTimerTitle: "Safety plan",
    safetyTimerDesc: "Automated check-ins and contact alerts are not available. Agree a plan with someone you trust; call 112 in an emergency.",
    safetyTimeRemaining: "Suggested time to check in with someone you trust:",

    // Social Proof & Social Media Connection
    socialProofTitle: "Social profile links",
    socialProofSub: "Adding a link does not verify a person's identity or the authenticity of the profile.",
    socialConnectBtn: "Connect",
    socialDisconnectBtn: "Disconnect",
    socialVerifiedBadge: "Linked",
    socialInstagram: "Instagram",
    socialLinkedIn: "LinkedIn",
    socialTikTok: "TikTok",
    socialFacebook: "Facebook",
    socialModalTitle: "Connect Social Profile",
    socialModalDesc: "Demo mode: entering a handle does not verify identity or account ownership.",
    socialHandleLabel: "Username or Profile Handle:",
    socialHandlePlaceholder: "e.g. @zuzanna.arch or zuzanna-wisniewska",
    socialConfirmConnect: "Save demo handle",
    socialSharePing: "Share Outing",
    socialShareSuccess: "Outing link copied for Instagram Stories or WhatsApp!",

    // Instagram & Dating App Look-alike features
    storiesTitle: "Neighbors heading out",
    yourStory: "+ Your Outing",
    viewModeFeed: "Outings",
    viewModeDeck: "Cards",
    viewModeMap: "Map",
    vibeMatch: "Vibe Match",
    deckNext: "Pass",
    deckMatch: "Request to join",
    deckSuperPing: "Super-Ping ⭐",
    whyGoing: "Why I'm heading out:",
    idealCompanion: "Looking for a buddy who:",
    likedTooltip: "Added to favorites! ❤️",
    bookmarkedTooltip: "Outing saved! 🔖",
    itsAnOuting: "You’ve connected! 🎉",
    celebrateSub: "Agree on the exact time and costs in chat. Both people must accept the plan.",
    openChatCoord: "Open Chat & Coordinate",
  },

  uk: {
    appName: "CartMate",
    locationDefault: "Катовіце, центр",
    radiusDefault: "радіус 8 км",
    radarTitle: "Радар Виходів Наживо",
    radarDesc: "Прогулянка, навчання, тренування, їжа чи справи разом. Спочатку погодьте публічне місце зустрічі та умови.",
    postRunBtn: "+ Додати Вихід",
    safeHavenFilter: "Жіноча Зона",
    safeHavenSub: "(Виходи виключно для жінок)",
    allPings: "Всі Виходи",
    catStudy: "📚 Навчання разом",
    catFitness: "🏃 Тренування / рух",
    catWalk: "🚶 Прогулянка",
    catFood: "🍽️ Спільний обід",
    catSocial: "💬 Розмова / компанія",
    catQuick: "⚡ Справи до вирішення",
    catGrocery: "🥦 Biedronka / Lidl / Продукти",
    catWholesale: "📦 Makro / Selgros (Опт)",
    catFashion: "🛍️ ТРЦ / Галереї / Шопінг",
    catHome: "🛋️ IKEA Катовіце / Дім",
    catLateNight: "🍔 Burger King & Нічне Гастро",
    catCafe: "☕ Кава & Коворкінг",
    catEntertainment: "🍿 Кіно / Прогулянки / Місто",
    noPings: "Немає активних виходів у цій категорії.",
    firstToPost: "Будьте першим, хто додасть вихід!",
    minutesLeft: "залишилось",
    away: "від Вас",
    joinRun: "Приєднатися",
    requests: "Заявки",
    requestModalTitle: "Приєднатися до спільного виходу",
    quickNoteLabel: "Швидке повідомлення організатору:",
    safetyTipTitle: "Правило Безпеки:",
    safetyTipText: "Погодьте конкретне публічне місце зустрічі. Не вказуйте приватну адресу; перевірте доступ і вартість місця.",
    cancel: "Скасувати",
    sendRequest: "Надіслати Заявку",
    sending: "Надсилання...",
    sent: "Надіслано!",
    reviewApplicants: "Заявки на вихід",
    noApplicantsYet: "Поки що немає заявок. Ваш вихід транслюється на місцевому радарі!",
    acceptCompanion: "Прийняти супутника та відкрити збір",

    // Create Ping
    postPingTitle: "Запросити когось на спільний вихід",
    broadcastSub: "Транслюється сусідам у радіусі кількох кілометрів",
    storePresetsLabel: "Публічні місця в Сілезії:",
    destNameLabel: "Назва Місця / Закладу",
    addressLabel: "Адреса / Вулиця",
    categoryLabel: "Категорія Виходу",
    activityVenueHint: "Оберіть публічне місце, яке легко знайти. Перевірте години й доступ; спортзал може вимагати абонемент. Узгодьте час і витрати в плані.",
    noExpectedSpend: "Без запланованих витрат",
    mutualConnectionsTitle: "Люди для наступної зустрічі",
    mutualConnectionsDesc: "Ви обоє захотіли зустрітися знову. Це не згода на контакт поза CartMate.",
    mutualConnectionsEmpty: "Після виходу кожен може вирішити, чи зустрітися знову. Без тиску.",
    sharedOutings: "спільних виходів",
    mutualContact: "Взаємна згода",
    meetAgainPrompt: "Чи хочете ви знову зустрітися з",
    mutualConfirmed: "Ви обоє хочете зустрітися знову. Ця людина є у вашому профілі.",
    noLongerNeeded: "Цей вихід більше не потрібен",
    planWhenLabel: "Дата й час",
    planMeetingPointLabel: "Точне публічне місце зустрічі",
    planMeetingPointHint: "Вкажіть вхід, площу чи інший зрозумілий орієнтир, не приватну адресу. Погодьте до прийняття плану.",
    lifespanLabel: "Час дії запису (зникне через):",
    intentTagsLabel: "Теги намірів і мети:",
    safeHavenToggleTitle: "Увімкнути Жіночу Зону (SafeHaven)",
    safeHavenToggleDesc: "Тільки верифіковані жінки бачитимуть цей вихід",
    companionNotesLabel: "Додаткова примітка для супутника",
    notesPlaceholder: "напр. Хочу повчитися годину в бібліотеці; зустрінемося біля головного входу.",
    publishToRadar: "🚀 Опублікувати на Радарі",
    publishing: "Публікація...",
    idRequiredTitle: "Потрібна Верифікація Особи",
    idRequiredDesc: "Для зустрічей лише для жінок потрібна справжня перевірка особи. Ця функція поки недоступна.",
    postOrdinaryDisclosure: "Приватний пілот: лише запрошені дорослі після схваленої перевірки 18+. Доступ через SMS або оператора сам по собі не підтверджує вік. Погодьте публічне місце, час і витрати до зустрічі.",
    verifyQuickBtn: "Переглянути статус перевірки",

    // Safety Hub
    safetyHubTitle: "Центр Довіри та Безпеки",
    safetyHubDesc: "Інструменти безпеки CartMate. Перевірка особи та налаштування екстреного контакту поки недоступні.",
    yourTier: "Ваш Рівень Верифікації:",
    tierBronzeTitle: "Рівень 1: Бронзовий (номер підтверджено SMS)",
    tierBronzeDesc: "SMS підтверджує лише номер телефону. Для публікації також потрібна схвалена перевірка віку 18+, яка ще недоступна.",
    tierBronzeUnconfirmedTitle: "Номер телефону не підтверджено",
    tierBronzeUnconfirmedDesc: "Підтвердження SMS саме по собі не дозволяє публікацію. Потрібна також схвалена перевірка віку 18+; демоакаунт її не забезпечує.",
    tierSilverTitle: "Рівень 2: Срібний (перевірка документа недоступна)",
    tierSilverDesc: "Для перевірки особи потрібен зовнішній сервіс; зараз вона недоступна.",
    tierSilverBtn: "✨ Верифікувати Особу (Симуляція)",
    tierSilverSuccess: "Успішно верифіковано! Присвоєно Срібний рівень.",
    tierGoldTitle: "Рівень 3: Золотий (Лідер Спільноти)",
    tierGoldDesc: "Запланований рівень; незалежна перевірка минулого наразі недоступна.",
    emergencyContactTitle: "Довірений Екстрений Контакт",
    emergencyContactDesc: "Налаштування екстреного контакту та підтвердження його згоди поки недоступні. У разі небезпеки телефонуйте 112.",
    activeBadge: "Активний",
    promiseTitle: "Стандарт Відповідального Додатка",
    promise1: "Жодної Нав'язливої Реклами: Ми не продаємо Вашу увагу та не профілюємо Вас.",
    promise2: "Без Доступу до Контактів: Ми ніколи не зчитуємо телефонну книгу Вашого смартфона.",
    promise3: "Справжнє Життя: Мета додатку — швидко знайти супутника та сховати смартфон у кишеню.",

    // Active Trip
    noActiveTripTitle: "Немає Активного Виходу",
    noActiveTripDesc: "Приєднайтесь до виходу на радарі або прийміть запит, щоб розпочати спільну прогулянку.",
    tripCancelledNotice: "Зустріч скасовано. Не їдьте до місця зустрічі; можете знайти інший план.",
    dismissNotice: "Закрити повідомлення",
    exploreRadarBtn: "Дивитися Радар",
    tripStatus: "Статус Виходу",
    statusAwaiting: "Очікування зустрічі біля входу",
    statusShopping: "Спільний вихід триває",
    statusSos: "🚨 ВІДКРИТО ОПЦІЇ ДОПОМОГИ",
    sosBtn: "SOS",
    designatedDest: "Місце Зустрічі",
    rendezvousLabel: "Точка Збору:",
    checkinStatusLabel: "Статус присутності:",
    checkinBoth: "Обидва на місці",
    checkinYou: "Ви на місці • Очікуєте супутника",
    checkinWaiting: "Натисніть після прибуття під вхід",
    arrivedBtn: "📍 Я на місці",
    companionHeader: "Ваш Супутник",
    chatHeader: "Чат Координації Виходу",
    chatPlaceholder: "Напишіть напр. 'Стою біля дверей у синій куртці'...",
    finishOutingBtn: "Завершити вихід",
    sosModalTitle: "Відкрити варіанти допомоги?",
    sosModalDesc: "CartMate не телефонує 112 і не надсилає SMS екстреному контакту. У разі небезпеки зателефонуйте 112 самостійно.",
    sosConfirmBtn: "Показати варіанти допомоги",
    sosConsentLabel: "Я розумію, що CartMate нікого не сповістить. У разі небезпеки я самостійно зателефоную 112.",
    sosOpeningLabel: "Відкриття...",
    sosFallbackNoDispatch: "CartMate нікого не сповістив. Зателефонуйте 112 самостійно.",
    sosFooter: "CartMate не замінює екстрені служби або дзвінок на 112.",
    sosDelivered: "Оператор підтвердив доставку повідомлення екстреному контакту.",
    sosDispatched: "Постачальник прийняв повідомлення; доставку ще не підтверджено.",
    completedOutingTitle: "Завершити вихід",
    completedOutingDesc: "Оцінка необов’язкова. Як пройшов спільний вихід із супутником?",
    submitReviewBtn: "Зберегти оцінку й завершити вихід",
    finishWithoutReviewBtn: "Завершити без оцінки",
    meetAgainOptional: "Необов’язково. Відповідь не вибрано за замовчуванням; зв’язок створюють лише два свідомі «Так».",
    outingCommentLabel: "Коментар про вихід",
    followUpSaveFailed: "Вихід завершено, але відповідь про повторну зустріч не збережено.",

    // Profile
    sharedTrips: "Спільні Виходи",
    ratingLabel: "Середня Оцінка",
    offlineHours: "Завершених виходів",
    viewCredentials: "Сертифікати та Бейджі",
    testPersonasTitle: "Тестові Профілі",
    testPersonasDesc: "Перемикайтесь між персонажами для тестування функціоналу:",
    impactTitle: "Вплив Спільноти CartMate у Польщі",
    impactTrips: "Здійснених Виходів",
    impactHours: "Подолано Самотності (Год)",
    impactSavings: "Заощаджено на Знижках",
    impactSafety: "Індекс Безпеки",
    currency: "zł",

    // Nav
    tabRadar: "Поблизу",
    tabNearby: "Поблизу",
    tabSafety: "Безпека",
    tabPost: "Створити",
    tabTrip: "Вихід",
    newChatMessage: "Нове повідомлення від супутника",
    tabProfile: "Профіль",

    // Living Community & Low-Friction Connection
    peopleNearby: "Люди поблизу",
    peopleShoppingNearby: "людей поруч планують вихід",
    privacyBannerText: "Приблизне місцезнаходження й публічні місця зустрічі — не домашні адреси.",
    actionWave: "👋 Помахати",
    actionJoin: "🤝 Приєднатися",
    actionAsk: "💬 Запитати",
    wavedSuccess: "Ви помахали сусіду! 👋",
    intentAll: "Всі",

    // Spot Voting & Demand Pooling
    spotVotingTitle: "Голосування за локації поблизу",
    spotVotingSub: "Зберемо компанію! Коли проголосує 3+ людей, спільний вихід формується автоматично.",
    spotVoteBtn: "Голосувати (+1)",
    spotVotedBtn: "Проголосовано ✓",
    spotGroupFormed: "🔥 Компанія готова до виходу!",
    spotJoinCrew: "Приєднатися до групи",
    suggestSpotBtn: "+ Запропонувати локацію",
    suggestModalTitle: "Запропонувати нове місце",

    // Auth & Navigation Enhancements
    authTitleLogin: "Вхід до CartMate",
    authTitleRegister: "Реєстрація в CartMate",
    authTabLogin: "Увійти",
    authTabRegister: "Зареєструватися",
    authIdentifierLabel: "Номер телефону",
    authIdentifierPlaceholder: "напр. +48 601 234 567",
    authCodeLabel: "Код підтвердження SMS OTP",
    authDemoQuickLogin: "Швидкий вхід через демо-профіль:",
    authLoginBtn: "Увійти безпечно",
    authRegisterBtn: "Створити акаунт",
    authFullName: "Ім'я та Прізвище",
    authGender: "Стать",
    authCity: "Місто пілоту в Сілезії",
    authBio: "Коротко про мене (інтереси / стиль виходів)",
    authLoggingIn: "Вхід...",
    authRegistering: "Реєстрація...",
    logoutBtn: "Вийти",
    switchAccountBtn: "Змінити акаунт / Вхід",
    citySelectTitle: "Оберіть місто пілоту в Сілезії:",
    radarMapTitle: "Візуальний Радар Локацій & Супутників",
    radarMapSub: "Натисніть на позначку на карті для перегляду виходу",

    // Innovations
    mannerTempTitle: "Температура Ввічливості (Manner)",
    mannerTempSub: "Показник за відгуками учасників; це не незалежна перевірка.",
    mannerBadgeWarm: "Теплий Супутник 🔥",
    mannerBadgesPunctual: "Пунктуальність ⏰",
    mannerBadgesPolite: "Висока Культура 🤝",
    mannerBadgesQuickSplit: "Прозорий розподіл витрат ⚡",
    mannerBadgesHelpful: "Уважний та Допоміжний 🛒",
    pinHandshakeTitle: "Спільний код зустрічі",
    pinHandshakeDesc: "PIN підтверджує, що обидві людини знають код зустрічі; застосунок не перевіряє місцезнаходження чи присутність.",
    yourPinLabel: "Ваш PIN-код зустрічі:",
    enterCompanionPin: "Введіть PIN-код супутника:",
    verifyPinBtn: "Підтвердити Зустріч",
    pinVerifiedBadge: "Введено однаковий PIN ✓",
    splitTabTitle: "Калькулятор витрат 50/50",
    splitTabDesc: "Запишіть суму й обчисліть приблизну половину. Застосунок не перевіряє чеки та не проводить платежі.",
    addItemSplitBtn: "+ Додати позицію до розподілу 50/50",
    itemNameLabel: "Назва страви / товару",
    itemPriceLabel: "Загальна сума (zł)",
    payerLabel: "Хто оплатив на касі?",
    split5050: "Розподіл 50/50",
    hostOwes: "Організатор повертає:",
    companionOwes: "Супутник повертає:",
    settleBlikBtn: "Скопіювати номер контакту",
    blikCopied: "Номер скопійовано. Платіж виконайте у власному банківському застосунку.",
    noItemsSplit: "Позицій ще не додано. Вкажіть бургер чи чек з магазину для розрахунку!",
    safetyTimerTitle: "План безпеки",
    safetyTimerDesc: "Автоматичні перевірки та сповіщення контакту недоступні. Домовтеся про план із близькою людиною; у разі небезпеки телефонуйте 112.",
    safetyTimeRemaining: "Рекомендований час для зв’язку з близькою людиною:",

    // Social Proof
    socialProofTitle: "Посилання на соціальні профілі",
    socialProofSub: "Посилання не підтверджує особу чи справжність профілю.",
    socialConnectBtn: "Підключити",
    socialDisconnectBtn: "Відключити",
    socialVerifiedBadge: "Підключено",
    socialInstagram: "Instagram",
    socialLinkedIn: "LinkedIn",
    socialTikTok: "TikTok",
    socialFacebook: "Facebook",
    socialModalTitle: "Підключити соціальний профіль",
    socialModalDesc: "Демо: введений ідентифікатор не підтверджує особу або володіння профілем.",
    socialHandleLabel: "Нікнейм або посилання:",
    socialHandlePlaceholder: "напр. @olha_art або olha-shevchenko",
    socialConfirmConnect: "Зберегти демо-ідентифікатор",
    socialSharePing: "Поділитися Виходом",
    socialShareSuccess: "Посилання на вихід скопійовано для Instagram Stories / Telegram / WhatsApp!",

    // Instagram & Dating App Look-alike features
    storiesTitle: "Сусіди виходять",
    yourStory: "+ Ваш Вихід",
    viewModeFeed: "Виходи",
    viewModeDeck: "Картки",
    viewModeMap: "Мапа",
    vibeMatch: "Сумісність Вайбу",
    deckNext: "Далі",
    deckMatch: "Попросити місце",
    deckSuperPing: "Супер-Пінг ⭐",
    whyGoing: "Чому сьогодні йду:",
    idealCompanion: "Шукаю супутника, який:",
    likedTooltip: "Додано в улюблені! ❤️",
    bookmarkedTooltip: "Вихід збережено! 🔖",
    itsAnOuting: "Ви домовилися про спільний вихід! 🎉",
    celebrateSub: "Узгодьте час і витрати в чаті. Обидва учасники мають підтвердити план.",
    openChatCoord: "Відкрити Чат Координації",
  },

  ru: {
    appName: "CartMate",
    locationDefault: "Катовице, центр",
    radiusDefault: "радиус 8 км",
    radarTitle: "Радар Встреч и Выходов",
    radarDesc: "Прогулка, учёба, тренировка, еда или дела вместе. Сначала согласуйте публичное место встречи и условия.",
    postRunBtn: "+ Добавить Выход",
    safeHavenFilter: "Женская Зона",
    safeHavenSub: "(Выходы только для женщин)",
    allPings: "Все Выходы",
    catStudy: "📚 Учиться вместе",
    catFitness: "🏃 Тренировка / движение",
    catWalk: "🚶 Прогулка",
    catFood: "🍽️ Поесть вместе",
    catSocial: "💬 Разговор / компания",
    catQuick: "⚡ Повседневные дела",
    catGrocery: "🥦 Biedronka / Lidl / Продукты",
    catWholesale: "📦 Makro / Selgros (Опт)",
    catFashion: "🛍️ ТЦ / Молл / Шопинг",
    catHome: "🛋️ IKEA Катовице / Дом",
    catLateNight: "🍔 Burger King & Ночной Перекус",
    catCafe: "☕ Кофе & Коворкинг",
    catEntertainment: "🍿 Кино / Город / Прогулки",
    noPings: "Нет активных выходов в выбранной категории.",
    firstToPost: "Будьте первым, кто создаст выход!",
    minutesLeft: "осталось",
    away: "от Вас",
    joinRun: "Присоединиться",
    requests: "Заявки",
    requestModalTitle: "Присоединиться к совместному выходу",
    quickNoteLabel: "Короткое сообщение организатору:",
    safetyTipTitle: "Правило Безопасности:",
    safetyTipText: "Согласуйте конкретное публичное место встречи. Не сообщайте домашний адрес; проверьте доступ и расходы.",
    cancel: "Отмена",
    sendRequest: "Отправить Заявку",
    sending: "Отправка...",
    sent: "Отправлено!",
    reviewApplicants: "Заявки на выход",
    noApplicantsYet: "Пока нет заявок. Ваш выход отображается на локальном радаре!",
    acceptCompanion: "Принять попутчика и открыть сбор",

    // Create Ping
    postPingTitle: "Пригласить кого-то на совместный выход",
    broadcastSub: "Транслируется соседям в радиусе нескольких километров",
    storePresetsLabel: "Общественные места в Силезии:",
    destNameLabel: "Название Места / Заведения",
    addressLabel: "Адрес / Улица",
    categoryLabel: "Категория Выхода",
    activityVenueHint: "Выберите публичное место, которое легко найти. Проверьте часы и доступ; зал может требовать абонемент. Согласуйте время и расходы в плане.",
    noExpectedSpend: "Без запланированных расходов",
    mutualConnectionsTitle: "Люди для новой встречи",
    mutualConnectionsDesc: "Вы оба захотели встретиться снова. Это не согласие на общение вне CartMate.",
    mutualConnectionsEmpty: "После выхода каждый может решить, встречаться ли снова. Без давления.",
    sharedOutings: "совместных выходов",
    mutualContact: "Взаимное согласие",
    meetAgainPrompt: "Хотите снова встретиться с",
    mutualConfirmed: "Вы оба хотите встретиться снова. Этот человек появится в вашем профиле.",
    noLongerNeeded: "Этот выход больше не нужен",
    planWhenLabel: "Дата и время",
    planMeetingPointLabel: "Точное публичное место встречи",
    planMeetingPointHint: "Укажите вход, площадь или другой понятный ориентир, не домашний адрес. Согласуйте до принятия плана.",
    lifespanLabel: "Срок действия записи (исчезнет через):",
    intentTagsLabel: "Теги намерений и цели:",
    safeHavenToggleTitle: "Включить Женскую Зону (SafeHaven)",
    safeHavenToggleDesc: "Только верифицированные женщины увидят этот выход",
    companionNotesLabel: "Дополнительная заметка для попутчика",
    notesPlaceholder: "напр. Хочу позаниматься час в библиотеке; встречаемся у главного входа.",
    publishToRadar: "🚀 Опубликовать на Радаре",
    publishing: "Публикация...",
    idRequiredTitle: "Требуется Верификация Личности",
    idRequiredDesc: "Для встреч только для женщин нужна настоящая проверка личности. Эта функция пока недоступна.",
    postOrdinaryDisclosure: "Частный пилот: только приглашённые взрослые после одобренной проверки 18+. Доступ через SMS или оператора сам по себе не подтверждает возраст. Согласуйте публичное место, время и расходы до встречи.",
    verifyQuickBtn: "Посмотреть статус проверки",

    // Safety Hub
    safetyHubTitle: "Центр Доверия и Безопасности",
    safetyHubDesc: "Инструменты безопасности CartMate. Проверка личности и настройка экстренного контакта пока недоступны.",
    yourTier: "Ваш Уровень Верификации:",
    tierBronzeTitle: "Уровень 1: Бронзовый (номер подтверждён SMS)",
    tierBronzeDesc: "SMS подтверждает только номер телефона. Для публикации также нужна одобренная проверка возраста 18+, которая пока недоступна.",
    tierBronzeUnconfirmedTitle: "Номер телефона не подтверждён",
    tierBronzeUnconfirmedDesc: "Одного подтверждения SMS недостаточно для публикации. Нужна также одобренная проверка возраста 18+; демоаккаунт её не обеспечивает.",
    tierSilverTitle: "Уровень 2: Серебряный (проверка документа недоступна)",
    tierSilverDesc: "Для проверки личности нужен внешний поставщик; сейчас она недоступна.",
    tierSilverBtn: "✨ Верифицировать Личность (Симуляция)",
    tierSilverSuccess: "Успешно подтверждено! Присвоен Серебряный уровень.",
    tierGoldTitle: "Уровень 3: Золотой (Лидер Сообщества)",
    tierGoldDesc: "Планируемый уровень; независимая проверка биографии пока недоступна.",
    emergencyContactTitle: "Доверенный Экстренный Контакт",
    emergencyContactDesc: "Настройка экстренного контакта и подтверждение его согласия пока недоступны. При угрозе звоните 112.",
    activeBadge: "Активен",
    promiseTitle: "Стандарт Этичного Приложения",
    promise1: "Ноль Навязчивой Рекламы: Мы не торгуем Вашим вниманием и не профилируем Вас.",
    promise2: "Без Сбора Контактов: Мы никогда не копируем телефонную книгу с Вашего устройства.",
    promise3: "Настоящая Жизнь: Задача сервиса — быстро найти попутчика и убрать телефон в карман.",

    // Active Trip
    noActiveTripTitle: "Нет Активного Выхода",
    noActiveTripDesc: "Присоединитесь к выходу на радаре или примите заявку, чтобы начать совместный выход.",
    tripCancelledNotice: "Встреча отменена. Не отправляйтесь к месту встречи; можно найти другой план.",
    dismissNotice: "Закрыть уведомление",
    exploreRadarBtn: "Смотреть Радар",
    tripStatus: "Статус Выхода",
    statusAwaiting: "Ожидание встречи у входа",
    statusShopping: "Совместный выход активен",
    statusSos: "🚨 ОТКРЫТЫ ВАРИАНТЫ ПОМОЩИ",
    sosBtn: "SOS",
    designatedDest: "Место Встречи",
    rendezvousLabel: "Точка Сбора:",
    checkinStatusLabel: "Статус присутствия:",
    checkinBoth: "Оба на месте",
    checkinYou: "Вы на месте • Ожидаете попутчика",
    checkinWaiting: "Нажмите по прибытии ко входу",
    arrivedBtn: "📍 Я на месте",
    companionHeader: "Ваш Попутчик",
    chatHeader: "Чат Координации Встречи",
    chatPlaceholder: "Напишите напр. 'Стою у входа в темной куртке'...",
    finishOutingBtn: "Завершить выход",
    sosModalTitle: "Открыть варианты помощи?",
    sosModalDesc: "CartMate не звонит на 112 и не отправляет SMS экстренному контакту. При опасности позвоните на 112 самостоятельно.",
    sosConfirmBtn: "Показать варианты помощи",
    sosConsentLabel: "Я понимаю, что CartMate никого не уведомит. При опасности я самостоятельно позвоню на 112.",
    sosOpeningLabel: "Открытие...",
    sosFallbackNoDispatch: "CartMate никого не уведомил. Позвоните на 112 самостоятельно.",
    sosFooter: "CartMate не заменяет экстренные службы или звонок на 112.",
    sosDelivered: "Оператор подтвердил доставку сообщения экстренному контакту.",
    sosDispatched: "Провайдер принял сообщение; доставка пока не подтверждена.",
    completedOutingTitle: "Завершить выход",
    completedOutingDesc: "Оценка необязательна. Как прошла совместная встреча с попутчиком?",
    submitReviewBtn: "Сохранить оценку и завершить выход",
    finishWithoutReviewBtn: "Завершить без оценки",
    meetAgainOptional: "Необязательно. Ответ не выбран по умолчанию; связь создают только два осознанных «Да».",
    outingCommentLabel: "Комментарий о встрече",
    followUpSaveFailed: "Встреча завершена, но ответ о повторной встрече не сохранён.",

    // Profile
    sharedTrips: "Совместные Выходы",
    ratingLabel: "Средняя Оценка",
    offlineHours: "Завершённых выходов",
    viewCredentials: "Сертификаты и Бейджи",
    testPersonasTitle: "Тестовые Профили",
    testPersonasDesc: "Переключайтесь между профилями для проверки разных сценариев:",
    impactTitle: "Влияние Сообщества CartMate в Польше",
    impactTrips: "Завершённых Выходов",
    impactHours: "Часов Сокращённого Одиночества",
    impactSavings: "Сэкономлено на Скидках",
    impactSafety: "Индекс Безопасности",
    currency: "zł",

    // Nav
    tabRadar: "Поблизости",
    tabNearby: "Поблизости",
    tabSafety: "Безопасность",
    tabPost: "Создать",
    tabTrip: "Выход",
    newChatMessage: "Новое сообщение от спутника",
    tabProfile: "Профиль",

    // Living Community & Low-Friction Connection
    peopleNearby: "Люди поблизости",
    peopleShoppingNearby: "человек поблизости планирует выход",
    privacyBannerText: "Примерное местоположение и публичные места встреч — не домашние адреса.",
    actionWave: "👋 Помахать",
    actionJoin: "🤝 Присоединиться",
    actionAsk: "💬 Спросить",
    wavedSuccess: "Вы помахали соседу! 👋",
    intentAll: "Все",

    // Spot Voting & Demand Pooling
    spotVotingTitle: "Голосование за локации поблизости",
    spotVotingSub: "Соберём компанию! Когда проголосует 3+ человека, совместный выход формируется автоматически.",
    spotVoteBtn: "Голосовать (+1)",
    spotVotedBtn: "Проголосовано ✓",
    spotGroupFormed: "🔥 Компания готова к выходу!",
    spotJoinCrew: "Присоединиться к группе",
    suggestSpotBtn: "+ Предложить локацию",
    suggestModalTitle: "Предложить новую локацию",

    // Auth & Navigation Enhancements
    authTitleLogin: "Вход в CartMate",
    authTitleRegister: "Регистрация в CartMate",
    authTabLogin: "Войти",
    authTabRegister: "Зарегистрироваться",
    authIdentifierLabel: "Номер телефона",
    authIdentifierPlaceholder: "напр. +48 601 234 567",
    authCodeLabel: "Код подтверждения SMS OTP",
    authDemoQuickLogin: "Быстрый вход через демо-аккаунт:",
    authLoginBtn: "Войти безопасно",
    authRegisterBtn: "Создать аккаунт",
    authFullName: "Имя и Фамилия",
    authGender: "Пол",
    authCity: "Город пилотного запуска в Силезии",
    authBio: "Коротко о себе (интересы / стиль выходов)",
    authLoggingIn: "Вход...",
    authRegistering: "Регистрация...",
    logoutBtn: "Выйти",
    switchAccountBtn: "Сменить аккаунт / Вход",
    citySelectTitle: "Выберите город пилотного запуска в Силезии:",
    radarMapTitle: "Визуальный Радар Локаций & Попутчиков",
    radarMapSub: "Нажмите на метку на карте, чтобы посмотреть выход",

    // Innovations
    mannerTempTitle: "Температура Вежливости (Manner)",
    mannerTempSub: "Показатель на основе отзывов участников; это не независимая проверка.",
    mannerBadgeWarm: "Тёплый Попутчик 🔥",
    mannerBadgesPunctual: "Пунктуальность ⏰",
    mannerBadgesPolite: "Высокая Культура 🤝",
    mannerBadgesQuickSplit: "Прозрачный раздел расходов ⚡",
    mannerBadgesHelpful: "Отзывчивый и Позитивный 🛒",
    pinHandshakeTitle: "Общий код встречи",
    pinHandshakeDesc: "PIN подтверждает, что оба человека знают код встречи; приложение не проверяет местоположение или физическое присутствие.",
    yourPinLabel: "Ваш PIN-код встречи:",
    enterCompanionPin: "Введите PIN-код попутчика:",
    verifyPinBtn: "Подтвердить Встречу",
    pinVerifiedBadge: "Введён совпадающий PIN ✓",
    splitTabTitle: "Калькулятор расходов 50/50",
    splitTabDesc: "Запишите сумму и рассчитайте примерную половину. Приложение не проверяет чеки и не проводит платежи.",
    addItemSplitBtn: "+ Добавить позицию к разделению 50/50",
    itemNameLabel: "Название блюда / покупки",
    itemPriceLabel: "Общая сумма (zł)",
    payerLabel: "Кто оплатил на кассе?",
    split5050: "Разделение 50/50",
    hostOwes: "Организатор возвращает:",
    companionOwes: "Попутчик возвращает:",
    settleBlikBtn: "Скопировать номер контакта",
    blikCopied: "Номер скопирован. Перевод выполните в своём банковском приложении.",
    noItemsSplit: "Пока нет позиций. Укажите заказ из Burger King или чек из магазина!",
    safetyTimerTitle: "План безопасности",
    safetyTimerDesc: "Автоматические проверки и уведомления контакта недоступны. Договоритесь о плане с близким человеком; при опасности звоните 112.",
    safetyTimeRemaining: "Рекомендуемое время для связи с близким человеком:",

    // Social Proof
    socialProofTitle: "Ссылки на социальные профили",
    socialProofSub: "Ссылка не подтверждает личность или подлинность профиля.",
    socialConnectBtn: "Подключить",
    socialDisconnectBtn: "Отключить",
    socialVerifiedBadge: "Подключено",
    socialInstagram: "Instagram",
    socialLinkedIn: "LinkedIn",
    socialTikTok: "TikTok",
    socialFacebook: "Facebook",
    socialModalTitle: "Подключить социальный профиль",
    socialModalDesc: "Демо: введённое имя аккаунта не подтверждает личность или владение профилем.",
    socialHandleLabel: "Никнейм или ссылка на профиль:",
    socialHandlePlaceholder: "напр. @dmitry_dev или dmitry-ivanov",
    socialConfirmConnect: "Сохранить демо-аккаунт",
    socialSharePing: "Поделиться Выходом",
    socialShareSuccess: "Ссылка на выход скопирована для Instagram Stories / Telegram / WhatsApp!",

    // Instagram & Dating App Look-alike features
    storiesTitle: "Соседи выходят",
    yourStory: "+ Ваш Выход",
    viewModeFeed: "Встречи",
    viewModeDeck: "Карточки",
    viewModeMap: "Карта",
    vibeMatch: "Совпадение Вайба",
    deckNext: "Пропустить",
    deckMatch: "Попросить место",
    deckSuperPing: "Супер-Пинг ⭐",
    whyGoing: "Почему сегодня выхожу:",
    idealCompanion: "Ищу попутчика, который:",
    likedTooltip: "Добавлено в избранное! ❤️",
    bookmarkedTooltip: "Выход сохранён! 🔖",
    itsAnOuting: "Вы договорились попробовать встретиться! 🎉",
    celebrateSub: "Согласуйте время и расходы в чате. Оба участника должны подтвердить план.",
    openChatCoord: "Открыть Чат Координации",
  },
};
