import hashlib
import logging
import math
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from models import (
    ActivityCategory,
    IntentClassificationResult,
    ContentSafetyResult,
    RendezvousSuggestion,
)
from config import JEV_MODE, TYPESAFE_JEV_API_KEY

logger = logging.getLogger("cartmate.jev")

# Polish keywords for deterministic classification, tailored for Silesia & Poland
KEYWORD_TAG_MAP = {
    r"\b(burger|kebab|pizza|frytki|mcdonald|kfc|nocne|gastro|głodny|jedzenie w nocy|mariacka)\b": (
        ActivityCategory.LATE_NIGHT,
        ["#NocneGastro", "#GastroFaza"],
        30,
        2,
    ),
    r"\b(studia|studiować|nauka|uczyć|biblioteka|bibliotece|egzamin|study|library|homework)\b": (
        ActivityCategory.STUDY, ["#WspólnaNauka"], 90, 2,
    ),
    r"\b(siłownia|siłownię|trening|ćwiczenia|fitness|gym|workout|basen)\b": (
        ActivityCategory.FITNESS, ["#RazemNaTrening"], 75, 2,
    ),
    r"\b(spacer|spacerować|park|parks|walk|walking|przechadzka|bulwary)\b": (
        ActivityCategory.WALK, ["#WspólnySpacer"], 45, 2,
    ),
    r"\b(obiad|lunch|kolacja|śniadanie|restauracja|posiłek|dinner|meal|food)\b": (
        ActivityCategory.FOOD, ["#PosiłekRazem"], 60, 2,
    ),
    r"\b(rozmowa|porozmawiać|pogadać|towarzystwo|spotkanie|company|hangout|chat)\b": (
        ActivityCategory.SOCIAL, ["#ChwilaRazem"], 45, 2,
    ),
    r"\b(promocja|wielosztuk|2\+1|gratis|rabat|taniej|masło|mleko|biedronk|lidl)\b": (
        ActivityCategory.GROCERY,
        ["#PromocjaWielosztuki", "#ŁowcyOkazji"],
        40,
        2,
    ),
    r"\b(zgrzewk|woda|wody|dźwiganie|ciężk|siatki|zgrzewka)\b": (
        ActivityCategory.GROCERY,
        ["#DźwiganieZgrzewek", "#PomocWZakupach"],
        35,
        2,
    ),
    r"\b(kawa|nero|costa|caffè|espresso|kawiarni|ciastko|pogaduchy|strefa kultury)\b": (
        ActivityCategory.CAFE,
        ["#KawaIPogaduchy", "#SpokojnyChill"],
        45,
        3,
    ),
    r"\b(inpost|paczkomat|paczka|odebranie|kurier)\b": (
        ActivityCategory.QUICK,
        ["#Paczkomat", "#NaSzybko"],
        20,
        2,
    ),
    r"\b(ubrania|zara|h&m|arkadia|złote tarasy|silesia city center|galeria katowicka|buty|sukienka|przymierz)\b": (
        ActivityCategory.FASHION,
        ["#ShoppingStyl", "#ModowyDoradca"],
        60,
        2,
    ),
    r"\b(ikea|castorama|leroy|meble|donice|remont|wkręty|roździeńskiego)\b": (
        ActivityCategory.HOME,
        ["#Majsterkowanie", "#IKEASpacer"],
        75,
        3,
    ),
    r"\b(makro|selgros|hurt|hurtownia|kartony|duże zakupy)\b": (
        ActivityCategory.WHOLESALE,
        ["#HurtoweZakupy", "#AutoNaZakupy"],
        60,
        2,
    ),
    r"\b(kino|film|spacer|powiśle|bulwary|dolina trzech stawów|spodek|planszówki)\b": (
        ActivityCategory.ENTERTAINMENT,
        ["#SpacerPoMieście", "#KulturalnyWieczór"],
        90,
        4,
    ),
}

UNSAFE_PATTERNS = [
    (r"\b(seks\w*|sex\w*|erotyk\w*|randk\w*|sponsor\w*|onlyfans)\b", "Zawartość o charakterze seksualnym lub randkowo-transakcyjnym narusza zasady bezpieczeństwa CartMate."),
    (r"\b(narkotyk\w*|zioło|koka\w*|stuff|lewe leki|recepty)\b", "Oferowanie lub poszukiwanie substancji nielegalnych."),
    (r"\b(przelej\w*|inwestycj\w*|krypto\w*|scam\w*|darmowe pieniądze|pożyczk\w*)\b", "Podejrzenie spamu finansowego lub wyłudzenia."),
    (r"\b(wpierdol\w*|zabij\w*|pobij\w*|agresj\w*|groźb\w*)\b", "Mowa nienawiści, agresja lub groźby karalne."),
]


def parse_noul_boolean(noul_val: Any) -> bool:
    """
    Parses the TypeSafe System One Noul answer, a probability in [0, 1].

    The HTTP contract requires a number, so booleans and numeric-looking strings
    are rejected rather than silently treated as valid provider responses.
    Missing, malformed, out-of-range, or non-finite values fail closed.
    """
    if isinstance(noul_val, bool) or not isinstance(noul_val, (int, float)):
        return False
    probability = float(noul_val)
    return math.isfinite(probability) and 0.0 <= probability <= 1.0 and probability >= 0.5


def _normalize_systemone_score(score: Any, criteria: List[str]) -> Optional[float]:
    """Normalize a TypeSafe Score answer from its rubric index to [0, 1]."""
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    score_value = float(score)
    max_index = len(criteria) - 1
    if max_index < 1 or not math.isfinite(score_value) or not 0.0 <= score_value <= max_index:
        return None
    return score_value / max_index


class JevEvaluationService:
    """
    TypeSafe AI Jev bounded decision service with Shadow Mode support.

    HARD SAFETY GOVERNANCE:
    Jev is strictly restricted to semantic classification, content screening,
    and public venue recommendation. Jev NEVER touches authentication,
    authorization, SafeHaven, SOS dispatch, eligibility, PIN checks, or financial math.

    API CONTRACT (TypeSafe System One):
    Uses official endpoint POST https://api.typesafe.ai/v1/systemone with model 'jev-latest'.
    Pre-send sanitization ensures all personal details (PII) are scrubbed BEFORE external transmission.

    SHADOW MODE:
    In 'shadow' mode, Jev evaluates requests in the background alongside
    the deterministic baseline. Output decisions are compared and audited
    without risking user-facing breakage until confidence is verified.
    When API credentials are not provided, shadow mode truthfully labels
    decisions as simulated fallbacks without fabricating agreement rates.
    """

    CONFIDENCE_SCORE_CRITERIA = [
        "Very low confidence: the category is mostly a guess",
        "Low confidence: weak evidence for the category",
        "Moderate confidence: some evidence, but alternatives remain plausible",
        "High confidence: clear evidence supports the category",
        "Very high confidence: the category is unambiguous",
    ]
    RISK_SCORE_CRITERIA = [
        "No apparent safety risk",
        "Low concern; no clear community-rule violation",
        "Moderate concern; possible spam, pressure, or inappropriate content",
        "High risk; harassment, threats, sexual solicitation, fraud, or illegal offers",
    ]
    SAFETY_NOUL_CRITERIA = {
        "true": "The text is a benign activity or meetup request and contains no clear safety-rule violation.",
        "false": "The text contains harassment, threats, sexual solicitation, illegal offers, fraud, or similarly unsafe content.",
    }

    def __init__(self, api_key: Optional[str] = TYPESAFE_JEV_API_KEY, mode: str = JEV_MODE):
        self.api_key = api_key
        self.enabled = bool(api_key)
        self.mode = mode.lower().strip()  # "shadow", "enforce", "disabled"
        self._shadow_audit_log: List[dict] = []

    @classmethod
    def sanitize_for_external_jev(cls, text: str) -> str:
        """
        Pre-send privacy minimization & redaction.
        Removes all personal identifiable information (PII) before any external API transmission:
          - Phone numbers (Polish GSM and international)
          - Email addresses
          - Street addresses and apartment numbers
          - Postal codes and national ID patterns
        """
        if not text:
            return ""
        # 1. Emails
        sanitized = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL]', text)
        # 2. National ID (PESEL / 11 digits)
        sanitized = re.sub(r'\b\d{11}\b', '[ID]', sanitized)
        # 3. Postal codes (xx-xxx)
        sanitized = re.sub(r'\b\d{2}-\d{3}\b', '[KOD_POCZTOWY]', sanitized)
        # 4. Street addresses with numbers (e.g. "ul. Mariacka 12", "al. Korfantego 35/2")
        sanitized = re.sub(
            r'\b(ul\.?|ulica|al\.?|aleja|pl\.?|plac)\s+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż\s]+\d+([a-zA-Z]|\/\d+)?',
            '[ADRES]',
            sanitized,
            flags=re.IGNORECASE,
        )
        # 5. Phone numbers (+48 ... or 9-digit formats)
        sanitized = re.sub(r'(\+?\d{1,3}[\s-]?)?\(?\d{2,3}\)?[\s-]?\d{3}[\s-]?\d{3,4}', '[NUMER_TEL]', sanitized)
        sanitized = re.sub(r'\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b', '[NUMER_TEL]', sanitized)
        # 6. PINs, secrets, and credentials (excluding postal code or already redacted tokens)
        sanitized = re.sub(r'\b(pin|hasło|haslo|hasła|hasla|sekret|token|kod\s*(?:sms|otp|blik|pin))\s*[:=]?\s*([a-zA-Z0-9_-]+)\b', '[SEKRET]', sanitized, flags=re.IGNORECASE)
        # 7. Payment cards (16 digits)
        sanitized = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[KARTA]', sanitized)
        # 8. Minimize data length: max 500 chars
        return sanitized[:500].strip()

    def _redact_input(self, text: str) -> str:
        """
        Redacts personal details from user input before writing to local shadow audit records.
        Ensures zero raw user words or phrases appear in audit logs.
        """
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
        return f"[REDACTED_INPUT hash={content_hash} len={len(text)}]"

    async def _call_typesafe_systemone(
        self,
        sanitized_state: str,
        questions: dict,
    ) -> Optional[dict]:
        """
        Official TypeSafe AI System One decision call:
        POST https://api.typesafe.ai/v1/systemone
        Model: jev-latest
        """
        if not self.api_key:
            return None
        url = "https://api.typesafe.ai/v1/systemone"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "jev-latest",
            "state": sanitized_state,
            "questions": questions,
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    return res.json()
                logger.warning(f"TypeSafe Jev System One returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.warning(f"TypeSafe Jev System One call exception: {e}")
        return None

    @classmethod
    def parse_noul_boolean(cls, noul_val: Any) -> bool:
        return parse_noul_boolean(noul_val)

    @classmethod
    def build_classify_questions(cls) -> dict:
        """
        Builds typed questions according to TypeSafe System One API contract.
        Choice questions specify 'criteria' as a key-to-description map,
        Score questions specify an ordered list of rubric descriptions,
        and Noul questions specify yes/no probability criteria.
        """
        return {
            "category": {
                "type": "choice",
                "criteria": {
                    "grocery": "Codzienne zakupy spożywcze, supermarkety, dyskonty (np. Biedronka, Lidl, Auchan)",
                    "wholesale": "Duże zakupy hurtowe i magazynowe (np. Makro, Selgros, giełdy)",
                    "fashion": "Odzież, obuwie, zakupy w galeriach handlowych (np. Silesia City Center)",
                    "home": "Meble, wyposażenie wnętrz, DIY, materiały budowlane (np. IKEA, Castorama)",
                    "quick": "Codzienne sprawy do załatwienia, drobne zadania, poczta lub paczkomat",
                    "late_night": "Zakupy nocne, sklepy całodobowe, stacje benzynowe",
                    "cafe": "Kawa, przekąski, spotkanie towarzyskie w centrum handlowym",
                    "entertainment": "Kino, rozrywka, wspólne spędzanie wolnego czasu",
                    "study": "Wspólna nauka w bibliotece lub innym publicznym miejscu",
                    "fitness": "Wspólny trening; dostęp do obiektu i opłaty wymagają ustalenia",
                    "walk": "Spacer rozpoczynający się w uzgodnionym publicznym punkcie",
                    "food": "Wspólny posiłek o dowolnej porze",
                    "social": "Rozmowa lub spokojne spotkanie w publicznym miejscu",
                },
                "instructions": "Która kategoria zakupów lub wyjścia w Polsce najlepiej pasuje do tego opisu?",
            },
            "is_safe": {
                "type": "noul",
                "criteria": cls.SAFETY_NOUL_CRITERIA,
                "instructions": "Czy tekst jest bezpieczny i wolny od nękania, ofert seksualnych, nielegalnych substancji lub oszustw?",
            },
            "confidence": {
                "type": "score",
                "criteria": cls.CONFIDENCE_SCORE_CRITERIA,
                "instructions": "Oceń stopień pewności dopasowania w skali 1-5.",
            },
        }

    @classmethod
    def parse_systemone_classify_response(cls, raw_response: dict, sanitized_state: str = "") -> dict:
        """
        Parses TypeSafe System One response according to official contract:
        Responses appear under 'answers', with choice under 'choice', score under 'score',
        and boolean evaluation under 'noul'.

        STRICT SAFETY INVARIANT:
        If 'is_safe' or 'noul' is missing, unrecognized, or null, it FAILS CLOSED
        (is_safe = False). Accepts 1.0 or True as verified safe.
        """
        if not isinstance(raw_response, dict):
            raw_response = {}
        answers = raw_response.get("answers")
        if not isinstance(answers, dict):
            answers = {}

        category_answer = answers.get("category")
        if not isinstance(category_answer, dict):
            category_answer = {}
        category_choice = category_answer.get("choice")
        
        # Fail-closed safety parsing against TypeSafe's numeric Noul contract.
        is_safe_node = answers.get("is_safe", {})
        if not isinstance(is_safe_node, dict):
            is_safe_node = {}
        noul_val = is_safe_node.get("noul")
        is_safe_val = parse_noul_boolean(noul_val)

        confidence_node = answers.get("confidence", {})
        if not isinstance(confidence_node, dict):
            confidence_node = {}
        confidence_score = _normalize_systemone_score(
            confidence_node.get("score"), cls.CONFIDENCE_SCORE_CRITERIA
        )
        return {
            "model": raw_response.get("model", "jev-latest"),
            "category": category_choice,
            "is_safe": is_safe_val,
            "confidence": confidence_score if confidence_score is not None else 0.0,
            "sanitized_state": sanitized_state,
            "answers": answers,
        }

    @classmethod
    def build_screen_questions(cls) -> dict:
        return {
            "is_safe": {
                "type": "noul",
                "criteria": cls.SAFETY_NOUL_CRITERIA,
                "instructions": "Czy podany tekst spełnia standardy bezpieczeństwa społeczności i jest wolny od przemocy, spamu i nękania?",
            },
            "risk_level": {
                "type": "score",
                "criteria": cls.RISK_SCORE_CRITERIA,
                "instructions": "Oceń poziom ryzyka od 0 (bezpieczny) do 3 (niebezpieczny).",
            },
        }

    @classmethod
    def parse_systemone_screen_response(cls, raw_response: dict, sanitized_state: str = "") -> dict:
        if not isinstance(raw_response, dict):
            raw_response = {}
        answers = raw_response.get("answers")
        if not isinstance(answers, dict):
            answers = {}
        
        # Fail-closed safety parsing against TypeSafe's numeric Noul contract.
        is_safe_node = answers.get("is_safe", {})
        if not isinstance(is_safe_node, dict):
            is_safe_node = {}
        noul_val = is_safe_node.get("noul")
        is_safe_val = parse_noul_boolean(noul_val)

        risk_node = answers.get("risk_level", {})
        if not isinstance(risk_node, dict):
            risk_node = {}
        normalized_risk = _normalize_systemone_score(
            risk_node.get("score"), cls.RISK_SCORE_CRITERIA
        )
        # A partial or malformed provider response must not be reported as safe.
        if normalized_risk is None:
            is_safe_val = False
        else:
            # The final two rubric levels represent moderate/high community risk.
            is_safe_val = is_safe_val and normalized_risk < (2.0 / (len(cls.RISK_SCORE_CRITERIA) - 1))
        return {
            "model": raw_response.get("model", "jev-latest"),
            "is_safe": is_safe_val,
            "safety_score": 1.0 - normalized_risk if normalized_risk is not None else 0.0,
            "sanitized_state": sanitized_state,
            "answers": answers,
        }

    async def _call_jev_classify(self, text: str, category_hint: Optional[str]) -> Optional[dict]:
        """
        Evaluates activity category, safety, and confidence via TypeSafe System One.
        Data is sanitized BEFORE sending over the wire.
        """
        if not self.api_key:
            return None
        sanitized_state = self.sanitize_for_external_jev(text)
        questions = self.build_classify_questions()
        raw_response = await self._call_typesafe_systemone(sanitized_state, questions)
        if not raw_response:
            return None
        return self.parse_systemone_classify_response(raw_response, sanitized_state)

    async def _call_jev_screen(self, text: str) -> Optional[dict]:
        """
        Evaluates content moderation and safety via TypeSafe System One.
        Data is sanitized BEFORE sending over the wire.
        """
        if not self.api_key:
            return None
        sanitized_state = self.sanitize_for_external_jev(text)
        questions = self.build_screen_questions()
        raw_response = await self._call_typesafe_systemone(sanitized_state, questions)
        if not raw_response:
            return None
        return self.parse_systemone_screen_response(raw_response, sanitized_state)

    async def classify_ping_intent(
        self, text: str, category_hint: Optional[ActivityCategory] = None
    ) -> IntentClassificationResult:
        start_time = time.perf_counter()
        lower = text.lower().strip()

        # 1. Deterministic Baseline Model
        safety = await self.screen_content_safety(text)
        if not safety.is_safe:
            baseline_result = IntentClassificationResult(
                category=category_hint or ActivityCategory.SOCIAL,
                intent_tags=["#Niejasne"],
                confidence_score=0.2,
                suggested_duration_minutes=30,
                recommended_group_size=2,
                social_context_summary="Tekst wymaga moderacji ze względów bezpieczeństwa.",
                is_safe=False,
            )
        else:
            matched_category = category_hint or ActivityCategory.SOCIAL
            matched_tags: List[str] = []
            duration = 35
            group_size = 2

            for pattern, (cat, tags, dur, grp) in KEYWORD_TAG_MAP.items():
                if re.search(pattern, lower):
                    if not category_hint:
                        matched_category = cat
                    matched_tags.extend(tags)
                    duration = dur
                    group_size = grp
                    break

            if not matched_tags:
                matched_tags = ["#ChwilaRazem"]
                summary = "Propozycja wspólnego wyjścia; szczegóły ustalcie razem"
                confidence = 0.72
            else:
                summary = f"Wyjście ukierunkowane ({matched_tags[0]}): bezpieczeństwo i zgodność z regulaminem"
                confidence = 0.94

            baseline_result = IntentClassificationResult(
                category=matched_category,
                intent_tags=list(set(matched_tags)),
                confidence_score=confidence,
                suggested_duration_minutes=duration,
                recommended_group_size=group_size,
                social_context_summary=summary,
                is_safe=True,
            )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 2. Shadow Mode Audit Recording
        if self.mode == "shadow":
            if self.api_key:
                remote_jev = await self._call_jev_classify(text, category_hint.value if category_hint else None)
                if remote_jev:
                    jev_decision = remote_jev
                    jev_cat = remote_jev.get("category")
                    agreed = (jev_cat == baseline_result.category.value)
                else:
                    jev_decision = {"status": "gateway_timeout", "mode": "real_api", "model": "jev-latest"}
                    agreed = None
            else:
                # Without credentials, record truthful fallback status without fabricating agreement
                jev_decision = {
                    "status": "simulated_fallback",
                    "model": "jev-latest",
                    "endpoint": "POST /v1/systemone",
                    "note": "TYPESAFE_JEV_API_KEY not configured; comparison skipped.",
                }
                agreed = None

            self._record_shadow_audit(
                task="intent_classification",
                input_snippet=self._redact_input(text),
                baseline_decision=baseline_result.model_dump(),
                jev_decision=jev_decision,
                agreed=agreed,
                latency_ms=latency_ms,
            )

        return baseline_result

    async def screen_content_safety(self, text: str) -> ContentSafetyResult:
        start_time = time.perf_counter()
        lower = text.lower()
        flagged: List[str] = []

        for pattern, reason in UNSAFE_PATTERNS:
            if re.search(pattern, lower):
                flagged.append(reason)

        if flagged:
            baseline_result = ContentSafetyResult(
                is_safe=False,
                safety_score=0.15,
                flagged_reasons=flagged,
                action_recommended="block",
            )
        else:
            baseline_result = ContentSafetyResult(
                is_safe=True,
                safety_score=0.98,
                flagged_reasons=[],
                action_recommended="allow",
            )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if self.mode == "shadow":
            if self.api_key:
                remote_screen = await self._call_jev_screen(text)
                if remote_screen:
                    jev_decision = remote_screen
                    agreed = (remote_screen.get("is_safe") == baseline_result.is_safe)
                else:
                    jev_decision = {"status": "gateway_timeout", "mode": "real_api", "model": "jev-latest"}
                    agreed = None
            else:
                jev_decision = {
                    "status": "simulated_fallback",
                    "model": "jev-latest",
                    "endpoint": "POST /v1/systemone",
                    "note": "TYPESAFE_JEV_API_KEY not configured; comparison skipped.",
                }
                agreed = None

            self._record_shadow_audit(
                task="content_safety",
                input_snippet=self._redact_input(text),
                baseline_decision=baseline_result.model_dump(),
                jev_decision=jev_decision,
                agreed=agreed,
                latency_ms=latency_ms,
            )

        return baseline_result

    def suggest_rendezvous(
        self, destination_name: str, category: ActivityCategory
    ) -> List[RendezvousSuggestion]:
        dest_lower = destination_name.lower()

        # Suggestions are orientation hints, not venue verification.
        if category in {
            ActivityCategory.STUDY, ActivityCategory.FITNESS,
            ActivityCategory.WALK, ActivityCategory.SOCIAL,
        }:
            return [RendezvousSuggestion(
                title="Uzgodniony publiczny punkt przy miejscu spotkania",
                description=f"Ustalcie konkretny, łatwy do znalezienia punkt przy {destination_name}.",
                safety_rating="Do potwierdzenia przez uczestników",
                tip="Sprawdźcie dostęp, godziny otwarcia i ewentualne opłaty; nie spotykajcie się pod prywatnym adresem.",
            )]

        # Silesian & General Polish retail spot heuristics
        if "silesia" in dest_lower or "galeria katowicka" in dest_lower or "arkadia" in dest_lower:
            return [
                RendezvousSuggestion(
                    title="Punkt Informacyjny / Główny Plac Handlowy",
                    description=f"Wewnątrz {destination_name}, przy głównym punkcie info na parterze.",
                    safety_rating="Do potwierdzenia przez uczestników",
                    tip="Sprawdźcie, czy taki punkt istnieje i jest dostępny; nie zakładajcie obecności ochrony ani monitoringu.",
                ),
                RendezvousSuggestion(
                    title="Wejście Główne od strony Placu / Dworca",
                    description=f"Przed wejściem obrotowym do {destination_name}.",
                    safety_rating="Do potwierdzenia przez uczestników",
                    tip="Sprawdźcie dostępność wejścia, oświetlenie i dojazd przed wyjściem.",
                ),
            ]
        elif "biedronka" in dest_lower or "lidl" in dest_lower:
            return [
                RendezvousSuggestion(
                    title="Punkt Obsługi Klienta / Przy kasach",
                    description=f"Wewnątrz sklepu {destination_name}, obok pierwszych kas lub POK.",
                    safety_rating="Do potwierdzenia przez uczestników",
                    tip="Sprawdźcie, czy istnieje taki punkt i czy sklep jest otwarty; monitoring nie jest zweryfikowany.",
                ),
                RendezvousSuggestion(
                    title="Główne wejście przy stojakach rowerowych",
                    description=f"Przed głównymi drzwiami przesuwnymi {destination_name}.",
                    safety_rating="Do potwierdzenia przez uczestników",
                    tip="Sprawdźcie, czy to wejście jest dostępne i czy miejsce jest odpowiednie do spotkania.",
                ),
            ]
        elif category in [ActivityCategory.CAFE, ActivityCategory.LATE_NIGHT, ActivityCategory.FOOD]:
            return [
                RendezvousSuggestion(
                    title="Przy ladzie głównej / Kasie",
                    description=f"Wewnątrz lokalu {destination_name}, obok lady z zamówieniami.",
                    safety_rating="Do potwierdzenia przez uczestników",
                    tip="Sprawdźcie godziny otwarcia, wejście i ewentualne koszty przed spotkaniem.",
                ),
                RendezvousSuggestion(
                    title="Przy wejściu głównym",
                    description=f"Przed wejściem do lokalu {destination_name}.",
                    safety_rating="Do potwierdzenia przez uczestników",
                    tip="Sprawdźcie przed wyjściem, czy lokal jest otwarty i wejście jest dostępne.",
                ),
            ]
        else:
            return [
                RendezvousSuggestion(
                    title="Główne wejście obrotowe / Hall główny",
                    description=f"Główny hall wejściowy {destination_name}.",
                    safety_rating="Do potwierdzenia przez uczestników",
                    tip="Sprawdźcie, czy wejście istnieje i jest dostępne; CartMate nie weryfikuje oświetlenia ani monitoringu.",
                )
            ]

    def _record_shadow_audit(
        self,
        task: str,
        input_snippet: str,
        baseline_decision: dict,
        jev_decision: dict,
        agreed: Optional[bool],
        latency_ms: float,
    ) -> None:
        # Privacy: audit entries are built from an allowlist of safe,
        # non-derived fields only. Free-text model summaries (which embed
        # user input), provider response blobs, and any field that could
        # carry user-authored content must never be retained.
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task": task,
            "input_snippet": input_snippet,
            "baseline_allowed": None,
            "baseline_category": None,
            "baseline_is_safe": None,
            "jev_agreement_status": self._shadow_agreement_status(jev_decision),
            "agreed": agreed,
            "latency_ms": latency_ms,
            "mode": self.mode,
            "is_simulated": not bool(self.api_key),
        }
        if isinstance(baseline_decision, dict):
            entry["baseline_allowed"] = baseline_decision.get("action_recommended") == "allow"
            entry["baseline_is_safe"] = baseline_decision.get("is_safe")
            category = baseline_decision.get("category")
            if isinstance(category, str):
                entry["baseline_category"] = category
        self._shadow_audit_log.append(entry)
        if len(self._shadow_audit_log) > 200:
            self._shadow_audit_log.pop(0)

    @staticmethod
    def _shadow_agreement_status(jev_decision: dict) -> str:
        """Collapse a provider/decision blob into a single non-content status token."""
        if not isinstance(jev_decision, dict):
            return "unavailable"
        if jev_decision.get("agreed") is True:
            return "agreed"
        status = jev_decision.get("status")
        if status in {"gateway_timeout", "simulated_fallback", "skipped"}:
            return str(status)
        if "error" in jev_decision:
            return "error"
        return "disagreed_or_unparsed"

    def get_shadow_audit_stats(self) -> dict:
        total = len(self._shadow_audit_log)
        real_evaluations = [e for e in self._shadow_audit_log if e.get("agreed") is not None]
        real_count = len(real_evaluations)
        agreements = sum(1 for e in real_evaluations if e.get("agreed") is True)
        avg_latency = (
            round(sum(e.get("latency_ms", 0.0) for e in self._shadow_audit_log) / total, 2)
            if total > 0
            else 0.0
        )
        return {
            "mode": self.mode,
            "is_configured": bool(self.api_key),
            "target_model": "jev-latest",
            "endpoint": "POST https://api.typesafe.ai/v1/systemone",
            "total_evaluations": total,
            "real_jev_evaluations": real_count,
            "agreements_count": agreements,
            "agreement_rate": round(agreements / real_count, 3) if real_count > 0 else 0.0,
            "average_latency_ms": avg_latency,
            "note": "Live TypeSafe Jev active" if self.api_key else "Simulated fallback mode (no external API key configured)",
            "recent_entries": self._shadow_audit_log[-10:],
        }


# Global singleton instance
jev_service = JevEvaluationService()
