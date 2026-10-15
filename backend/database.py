import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from models import (
    ActivityCategory,
    ChatMessageSchema,
    ChatRoomSchema,
    HotspotSpotSchema,
    JoinRequestSchema,
    LivePingSchema,
    OutingSchema,
    PingStatus,
    PlanDetailsSchema,
    RequestStatus,
    TripItemSplit,
    TripParticipantUserSchema,
    TripSchema,
    TripStatus,
    TrustTier,
    UserSchema,
    ReportSchema,
    ShoppingBuddySchema,
)
from storage import storage
from config import is_production

DEMO_USER_IDS = frozenset({"usr_zuzanna", "usr_jakub", "usr_ania", "usr_ola", "usr_marek", "usr_mateusz"})

# User blocks tracking: (blocker_id, blocked_id)
BLOCKED_USERS: set = set()
# Reports store: id -> ReportSchema
REPORTS: Dict[str, ReportSchema] = {}
# Shopping buddies store: user_id -> List of buddy dicts
SHOPPING_BUDDIES: Dict[str, List[dict]] = {}

# Simulated in-memory database tailored for Silesia Launch (Katowice & Górnośląsko-Zagłębiowska Metropolia)
USERS: Dict[str, UserSchema] = {
    "usr_zuzanna": UserSchema(
        id="usr_zuzanna",
        name="Zuzanna Wiśniewska",
        email="zuzanna.w@example.pl",
        phone="+48 601 234 567",
        avatar="",
        bio="Studentka architektury wnętrz na UŚ. Uwielbiam bazarki, Nikiszowiec, Mariacką i polowanie na perełki do mieszkania.",
        trust_tier=TrustTier.SILVER,
        gender="female",
        city="Katowice",
        safe_haven_enabled=True,
        is_id_verified=True,
        is_selfie_verified=True,
        is_background_checked=False,
        campus_badge="Uniwersytet Śląski '26",
        rating=4.96,
        manner_temperature=38.4,
        reviews_count=19,
        trips_completed=14,
        emergency_contact="+48 609 888 111 (Siostra Marta)",
        instagram_handle="@zuzanna.arch",
        instagram_verified=True,
        linkedin_handle="zuzanna-wisniewska",
        linkedin_verified=True,
    ),
    "usr_jakub": UserSchema(
        id="usr_jakub",
        name="Jakub Kamiński",
        email="jakub.k@example.pl",
        phone="+48 502 876 543",
        avatar="",
        bio="Karta Makro & Selgros Katowice VIP. Pasjonat dobrej kuchni. Szukam chętnych do dzielenia dużych zgrzewek i wielopaków.",
        trust_tier=TrustTier.GOLD,
        gender="male",
        city="Katowice",
        safe_haven_enabled=False,
        is_id_verified=True,
        is_selfie_verified=True,
        is_background_checked=True,
        campus_badge=None,
        rating=5.0,
        manner_temperature=41.2,
        reviews_count=38,
        trips_completed=31,
        emergency_contact="+48 501 333 999 (Partnerka Kasia)",
        instagram_handle="@kuba_chef",
        instagram_verified=True,
        linkedin_handle="jakub-kaminski-pl",
        linkedin_verified=True,
    ),
    "usr_ania": UserSchema(
        id="usr_ania",
        name="Ania Dąbrowska",
        email="ania.d@example.pl",
        phone="+48 791 432 109",
        avatar="",
        bio="Studentka Politechniki Śląskiej. Fanka promocji wielosztuk w Biedronce i Lidlu oraz modowych wypadów do Silesia City Center.",
        trust_tier=TrustTier.BRONZE,
        gender="female",
        city="Gliwice",
        safe_haven_enabled=False,
        is_id_verified=False,
        is_selfie_verified=False,
        is_background_checked=False,
        campus_badge="Politechnika Śląska '27",
        rating=4.85,
        manner_temperature=36.8,
        reviews_count=5,
        trips_completed=4,
        emergency_contact=None,
        instagram_handle="@ania.polsl",
        instagram_verified=True,
        tiktok_handle="@ania_deals",
        tiktok_verified=True,
    ),
    "usr_mateusz": UserSchema(
        id="usr_mateusz",
        name="Mateusz Zieliński",
        email="mateusz.z@example.pl",
        phone="+48 510 998 776",
        avatar="",
        bio="Fan technologii i dobrej kawy. Często w Dolinie Trzech Stawów i na Mariackiej. Chętnie podzielę koszty przejazdu!",
        trust_tier=TrustTier.SILVER,
        gender="male",
        city="Sosnowiec",
        safe_haven_enabled=False,
        is_id_verified=True,
        is_selfie_verified=True,
        is_background_checked=False,
        campus_badge="Uniwersytet Śląski '25",
        rating=4.92,
        manner_temperature=37.5,
        reviews_count=11,
        trips_completed=8,
        emergency_contact="+48 510 111 222 (Brat Tomasz)",
        linkedin_handle="mateusz-zielinski-us",
        linkedin_verified=True,
    ),
    "usr_ola": UserSchema(
        id="usr_ola",
        name="Ola Kowalska",
        email="ola.k@example.pl",
        phone="+48 603 555 777",
        avatar="",
        bio="Projektantka UX. Gotuję z pasją, szukam towarzystwa na szybkie zakupy spożywcze i inspiracje kulinarne.",
        trust_tier=TrustTier.SILVER,
        gender="female",
        city="Katowice",
        safe_haven_enabled=True,
        is_id_verified=True,
        is_selfie_verified=True,
        is_background_checked=False,
        campus_badge="ASP Katowice '24",
        rating=4.95,
        manner_temperature=39.1,
        reviews_count=14,
        trips_completed=11,
        emergency_contact="+48 600 222 333 (Mama)",
        instagram_handle="@ola_cooks_pl",
        instagram_verified=True,
    ),
    "usr_marek": UserSchema(
        id="usr_marek",
        name="Marek Nowak",
        email="marek.n@example.pl",
        phone="+48 504 333 888",
        avatar="",
        bio="Miłośnik kina i gotowania. Doceniam dobre składniki i luźną pogawędkę zamiast samotności.",
        trust_tier=TrustTier.GOLD,
        gender="male",
        city="Warszawa",
        safe_haven_enabled=False,
        is_id_verified=True,
        is_selfie_verified=True,
        is_background_checked=True,
        campus_badge=None,
        rating=4.98,
        manner_temperature=40.4,
        reviews_count=27,
        trips_completed=22,
        emergency_contact="+48 501 444 888 (Brat Paweł)",
        linkedin_handle="marek-nowak-tech",
        linkedin_verified=True,
    ),
}

# Current session holder (defaults to Zuzanna)
CURRENT_USER_ID = "usr_zuzanna"

# Live Stores
PINGS: Dict[str, LivePingSchema] = {}
JOIN_REQUESTS: Dict[str, List[JoinRequestSchema]] = {}
TRIPS: Dict[str, TripSchema] = {}
HOTSPOTS: Dict[str, HotspotSpotSchema] = {}
OUTINGS: Dict[str, OutingSchema] = {}
CHAT_ROOMS: Dict[str, ChatRoomSchema] = {}


def find_user_by_identifier(identifier: str) -> Optional[UserSchema]:
    clean_id = identifier.strip().lower()
    clean_digits = "".join(char for char in clean_id if char.isdigit())
    # Polish numbers may be entered as +48XXXXXXXXX or XXXXXXXXX. Never use
    # substring/suffix matching: an OTP for one number must not select another account.
    canonical_phone = clean_digits[2:] if clean_digits.startswith("48") and len(clean_digits) == 11 else clean_digits

    for user in USERS.values():
        if user.email.strip().lower() == clean_id:
            return user
        user_digits = "".join(char for char in user.phone if char.isdigit())
        user_phone = user_digits[2:] if user_digits.startswith("48") and len(user_digits) == 11 else user_digits
        if canonical_phone and user_phone == canonical_phone:
            return user
    return None


def create_user(
    name: str,
    email: str,
    phone: str,
    gender: str,
    city: str = "Warszawa",
    bio: str = "Nowy użytkownik CartMate.",
    campus_badge: Optional[str] = None,
    phone_verified_at: Optional[str] = None,
    pilot_invite_code: Optional[str] = None,
) -> UserSchema:
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    # Never assign a stock person's face to a real new account. The client
    # renders a neutral initials avatar until a genuine upload flow exists.
    avatar = ""
    new_user = UserSchema(
        id=user_id,
        name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        avatar=avatar,
        bio=bio.strip(),
        trust_tier=TrustTier.BRONZE,
        gender=gender,
        city=city,
        safe_haven_enabled=False,
        is_id_verified=False,
        is_selfie_verified=False,
        is_background_checked=False,
        campus_badge=campus_badge,
        rating=5.0,
        reviews_count=0,
        trips_completed=0,
        emergency_contact=None,
        phone_verified_at=phone_verified_at,
    )
    if pilot_invite_code:
        storage.persist_user_with_pilot_invite(new_user.model_dump(), pilot_invite_code)
    else:
        storage.persist_user(new_user.model_dump())
    USERS[user_id] = new_user
    return new_user


def save_trip(trip: TripSchema) -> TripSchema:
    TRIPS[trip.id] = trip
    storage.persist_trip(trip.model_dump())
    return trip


def save_ping(ping: LivePingSchema) -> LivePingSchema:
    PINGS[ping.id] = ping
    storage.persist_ping(ping.model_dump())
    return ping


def save_join_request(join_request: JoinRequestSchema) -> JoinRequestSchema:
    storage.persist_join_request(join_request.model_dump())
    requests = JOIN_REQUESTS.setdefault(join_request.ping_id, [])
    if not any(existing.id == join_request.id for existing in requests):
        requests.append(join_request)
    return join_request


def save_hotspot(spot: HotspotSpotSchema) -> HotspotSpotSchema:
    HOTSPOTS[spot.id] = spot
    storage.persist_hotspot(spot.model_dump())
    return spot


def record_hotspot_vote(spot_id: str, user_id: str):
    storage.persist_hotspot_vote(spot_id, user_id)


def remove_hotspot_vote(spot_id: str, user_id: str):
    storage.remove_hotspot_vote(spot_id, user_id)


def save_outing(outing: OutingSchema) -> OutingSchema:
    OUTINGS[outing.id] = outing
    storage.persist_outing(outing.model_dump())
    return outing


def save_chat_room(room: ChatRoomSchema) -> ChatRoomSchema:
    CHAT_ROOMS[room.id] = room
    storage.persist_chat_room(room.model_dump())
    return room


def save_chat_message(room_id: str, message: ChatMessageSchema):
    storage.persist_chat_message(room_id, message.model_dump())
    if room_id in CHAT_ROOMS:
        storage.persist_chat_room(CHAT_ROOMS[room_id].model_dump())


def seed_initial_data():
    now = datetime.now(timezone.utc)
    
    # 1. Makro Cash & Carry Katowice wholesale split by Jakub
    p1_id = "png_makro_01"
    PINGS[p1_id] = LivePingSchema(
        id=p1_id,
        host=USERS["usr_jakub"],
        category=ActivityCategory.WHOLESALE,
        destination_name="Makro Cash & Carry Katowice",
        destination_lat=50.2680,
        destination_lng=19.0400,
        address="Al. Roździeńskiego 188, Katowice",
        intent_tags=["#KartaMakroVIP", "#DzielenieWielosztuk", "#OliwaSerWędliny", "#ZakupyNaPół"],
        notes="Wjeżdżam do Makro Katowice po włoskie sery, oliwę i chemię w 5-litrowych kanistrach. Mogę wprowadzić na moją kartę firmową i dzielimy paczki 50/50!",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=12)).isoformat(),
        expires_at=(now + timedelta(minutes=48)).isoformat(),
        remaining_seconds=48 * 60,
        join_requests_count=1,
    )
    JOIN_REQUESTS[p1_id] = [
        JoinRequestSchema(
            id=str(uuid.uuid4())[:8],
            ping_id=p1_id,
            applicant=USERS["usr_ania"],
            message="Cześć Jakub! Chętnie dołączę do Makro i podzielę dużą paczkę papieru ręcznikowego i oliwę!",
            status=RequestStatus.PENDING,
            created_at=(now - timedelta(minutes=4)).isoformat(),
        )
    ]

    # 2. Biedronka - promocje wielosztuk by Zuzanna (Katowice Centrum)
    p2_id = "png_biedronka_02"
    PINGS[p2_id] = LivePingSchema(
        id=p2_id,
        host=USERS["usr_zuzanna"],
        category=ActivityCategory.GROCERY,
        destination_name="Biedronka Katowice",
        destination_lat=50.2600,
        destination_lng=19.0220,
        address="Al. Korfantego / Rynek, Katowice",
        intent_tags=["#PromocjaWielosztuki", "#StrefaKobiet", "#SpokojneZakupy", "#KawaNaWynos"],
        notes="Robię tygodniowe zakupy. W gazetce jest 'Kup 2 zapłać 50% mniej' na kawę i bakalie. Szukam towarzyszki ze Śląska, żeby skorzystać z rabatu!",
        women_only=True,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=8)).isoformat(),
        expires_at=(now + timedelta(minutes=37)).isoformat(),
        remaining_seconds=37 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p2_id] = []

    # 3. Silesia City Center fashion by Ania
    p3_id = "png_tarasy_03"
    PINGS[p3_id] = LivePingSchema(
        id=p3_id,
        host=USERS["usr_ania"],
        category=ActivityCategory.FASHION,
        destination_name="Silesia City Center & Zara",
        destination_lat=50.2700,
        destination_lng=19.0040,
        address="ul. Chorzowska 107, Katowice",
        intent_tags=["#DrugaOpinia", "#JesiennePłaszcze", "#Stylizacja", "#KawaPoZakupach"],
        notes="Szukam kogoś, kto pomoże mi ocenić płaszcz i buty w Silesii. Po przymierzalniach zapraszam na kawę do Starbucks lub bubble tea!",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=5)).isoformat(),
        expires_at=(now + timedelta(minutes=55)).isoformat(),
        remaining_seconds=55 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p3_id] = []

    # 4. IKEA Katowice home goods
    p4_id = "png_ikea_04"
    PINGS[p4_id] = LivePingSchema(
        id=p4_id,
        host=USERS["usr_jakub"],
        category=ActivityCategory.HOME,
        destination_name="IKEA Katowice",
        destination_lat=50.2690,
        destination_lng=19.0550,
        address="Al. Roździeńskiego 95, Katowice",
        intent_tags=["#PomocWZnoszeniu", "#DoposażenieMieszkania", "#KlopsikiIkea"],
        notes="Jadę autem kombi odebrać regał KALLAX i drobiazgi do kuchni. Mam wolne miejsce w bagażniku, mogę zabrać kogoś po drodze z Katowic lub Sosnowca!",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=15)).isoformat(),
        expires_at=(now + timedelta(minutes=65)).isoformat(),
        remaining_seconds=65 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p4_id] = []

    # 5. Forum Gliwice / Carrefour by Mateusz (Silesia - Gliwice)
    p5_id = "png_krakow_05"
    PINGS[p5_id] = LivePingSchema(
        id=p5_id,
        host=USERS["usr_mateusz"],
        category=ActivityCategory.QUICK,
        destination_name="Forum Gliwice & Carrefour",
        destination_lat=50.2945,
        destination_lng=18.6714,
        address="ul. Lipowa 1, Gliwice",
        intent_tags=["#KawaPoZajęciach", "#DrobneZakupy", "#Rozmowa"],
        notes="Przerwa między zajęciami na PolSl. Idę po kawę i zakupy na obiad. Zapraszam kogoś ze Śląska do towarzystwa na 40 minut!",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=7)).isoformat(),
        expires_at=(now + timedelta(minutes=45)).isoformat(),
        remaining_seconds=45 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p5_id] = []

    # 6. Burger King 24h Late-Night Run (Katowice Dworzec PKP)
    p6_id = "png_burgerking_06"
    PINGS[p6_id] = LivePingSchema(
        id=p6_id,
        host=USERS["usr_jakub"],
        category=ActivityCategory.LATE_NIGHT,
        destination_name="Burger King Katowice Dworzec 24h",
        destination_lat=50.2580,
        destination_lng=19.0175,
        address="Plac Szewczyka 2 (Dworzec PKP), Katowice",
        intent_tags=["#NocneGastro", "#GłodnyONocy", "#BurgerKingRun", "#NieChcęJeśćSam", "#RozmowaPrzyFrytkach"],
        notes="Jest późny wieczór po pracy. Idę do Burger Kinga na Dworcu w Katowicach na Whoppera i frytki. Ktoś chętny dołączyć na 30-40 minut pogadać i coś zjeść?",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=10)).isoformat(),
        expires_at=(now + timedelta(minutes=35)).isoformat(),
        remaining_seconds=35 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p6_id] = []

    # 7. Kafej / Strefa Kultury - Co-working & Coffee (Katowice)
    p7_id = "png_cafe_07"
    PINGS[p7_id] = LivePingSchema(
        id=p7_id,
        host=USERS["usr_ania"],
        category=ActivityCategory.CAFE,
        destination_name="Kafej / Strefa Kultury",
        destination_lat=50.2575,
        destination_lng=19.0260,
        address="ul. Mariacka / Strefa Kultury, Katowice",
        intent_tags=["#PracaZLaptopem", "#KawaIRozmowa", "#DrugaOpinia", "#NieSiedźWSamocie"],
        notes="Siedzę z laptopem nad projektem. Zapraszam na kawę i sernik baskijski, miło będzie popracować wspólnie przy jednym stoliku!",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=12)).isoformat(),
        expires_at=(now + timedelta(minutes=48)).isoformat(),
        remaining_seconds=48 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p7_id] = []

    # 8. Lidl Katowice - Ola's movie night snacks run
    p8_id = "png_lidl_08"
    PINGS[p8_id] = LivePingSchema(
        id=p8_id,
        host=USERS["usr_ola"],
        category=ActivityCategory.GROCERY,
        destination_name="Lidl Katowice Chorzowska",
        destination_lat=50.2610,
        destination_lng=19.0150,
        address="ul. Chorzowska 19, Katowice",
        intent_tags=["#Snacks", "#Grocery", "#MovieNight", "#Shopping", "#PrzekąskiNaWieczór"],
        notes="Kupuję nachosy, dipy i coś słodkiego na wieczór filmowy. Miło będzie skoczyć razem do Lidla i pogadać!",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=6)).isoformat(),
        expires_at=(now + timedelta(minutes=42)).isoformat(),
        remaining_seconds=42 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p8_id] = []

    # 9. Biedronka Mariacka - Marek finding good tomatoes
    p9_id = "png_biedronka_09"
    PINGS[p9_id] = LivePingSchema(
        id=p9_id,
        host=USERS["usr_marek"],
        category=ActivityCategory.GROCERY,
        destination_name="Biedronka Mariacka",
        destination_lat=50.2570,
        destination_lng=19.0270,
        address="ul. Mariacka 2, Katowice",
        intent_tags=["#Tomatoes", "#Healthy", "#Cooking", "#Grocery", "#DobrePomidory"],
        notes="Szukam dobrych dojrzałych pomidorów do śląskiego obiadu. Chętnie podzielę zakupy lub pogadam o gotowaniu.",
        women_only=False,
        status=PingStatus.ACTIVE,
        created_at=(now - timedelta(minutes=9)).isoformat(),
        expires_at=(now + timedelta(minutes=50)).isoformat(),
        remaining_seconds=50 * 60,
        join_requests_count=0,
    )
    JOIN_REQUESTS[p9_id] = []

    # 10. Seeded Active Trip between Jakub (Host) and Zuzanna (Companion) at Makro Cash & Carry
    t1_id = "trip_makro_01"
    TRIPS[t1_id] = TripSchema(
        id=t1_id,
        ping_id=p1_id,
        host=TripParticipantUserSchema(**USERS["usr_jakub"].model_dump()),
        companion=TripParticipantUserSchema(**USERS["usr_zuzanna"].model_dump()),
        destination_name="Makro Cash & Carry Katowice",
        rendezvous_spot="Punkt Obsługi Klienta / Wejście Główne (Al. Roździeńskiego 188)",
        status=TripStatus.SCHEDULED,
        host_checked_in=True,
        companion_checked_in=False,
        host_accepted=True,
        companion_accepted=True,
        plan_details=PlanDetailsSchema(
            what="Wspólne zakupy hurtowe Makro Katowice",
            when="Dzisiaj, 18:30",
            estimated_duration_minutes=45,
            cost_policy="split_strictly_50_50",
            estimated_cost_pln=200.0,
        ),
        rendezvous_pin="4819",
        rendezvous_verified=False,
        safety_deadline_minutes=45,
        items_split=[
            TripItemSplit(
                id="split_01",
                item_name="Oliwa Extra Virgin 5L (Makro Chef)",
                total_price_pln=139.90,
                payer_id="usr_jakub",
                host_owes_pln=0.0,
                companion_owes_pln=69.95,
                created_at=(now - timedelta(minutes=2)).isoformat(),
            )
        ],
        total_split_pln=139.90,
        created_at=(now - timedelta(minutes=10)).isoformat(),
        sos_triggered=False,
        chat_room_id="chat_trip_makro_01",
    )

    # 11. Seeded Hotspots (Silesia launch market: Katowice)
    HOTSPOTS["spot_bk_centralny"] = HotspotSpotSchema(
        id="spot_bk_centralny",
        city="Katowice",
        name="Burger King Katowice Dworzec 24h",
        category=ActivityCategory.LATE_NIGHT,
        emoji="🍔",
        address="Plac Szewczyka 2 (Dworzec PKP), Katowice",
        target_time="23:30 (Dzisiaj)",
        description="Nocne gastro po pracy/uczelni w Katowicach. Nie chcę jeść burgera samemu przy pustym stoliku!",
        cost_policy="Każdy płaci za siebie",
        votes_count=2,
        voter_ids=["usr_jakub", "usr_mateusz"],
        voter_avatars=[
            USERS["usr_jakub"].avatar,
            USERS["usr_mateusz"].avatar,
        ],
        threshold=3,
        group_formed=False,
        created_at=(now - timedelta(hours=2)).isoformat(),
    )

    HOTSPOTS["spot_biedronka_marszalkowska"] = HotspotSpotSchema(
        id="spot_biedronka_marszalkowska",
        city="Katowice",
        name="Biedronka Mariacka Katowice",
        category=ActivityCategory.GROCERY,
        emoji="🛒",
        address="ul. Mariacka 2, Katowice",
        target_time="19:00 (Jutro)",
        description="Polowanie na promocję 'Kup 2, zapłać 50% za drugi'. Szukam kogoś do podziału wielopaków!",
        cost_policy="Podział 50/50 BLIK na miejscu",
        votes_count=1,
        voter_ids=["usr_zuzanna"],
        voter_avatars=[USERS["usr_zuzanna"].avatar],
        threshold=3,
        group_formed=False,
        created_at=(now - timedelta(hours=3)).isoformat(),
    )

    HOTSPOTS["spot_cafe_nero"] = HotspotSpotSchema(
        id="spot_cafe_nero",
        city="Katowice",
        name="Kafej / Strefa Kultury",
        category=ActivityCategory.CAFE,
        emoji="☕",
        address="ul. Uniwersytecka 13, Katowice",
        target_time="14:00 (Sobota)",
        description="Wspólna praca z laptopem + kawa. Duży stół, dobra energia, zero presji na small talk.",
        cost_policy="Każdy zamawia własną kawę",
        votes_count=3,
        voter_ids=["usr_ania", "usr_ola", "usr_zuzanna"],
        voter_avatars=[
            USERS["usr_ania"].avatar,
            USERS["usr_ola"].avatar,
            USERS["usr_zuzanna"].avatar,
        ],
        threshold=3,
        group_formed=True,
        outing_id="out_cafe_nero_01",
        created_at=(now - timedelta(hours=4)).isoformat(),
    )

    out_id = "out_cafe_nero_01"
    chat_id = "room_out_cafe_nero_01"
    OUTINGS[out_id] = OutingSchema(
        id=out_id,
        hotspot_id="spot_cafe_nero",
        hotspot_name="Kafej / Strefa Kultury",
        category=ActivityCategory.CAFE,
        emoji="☕",
        city="Katowice",
        address="ul. Uniwersytecka 13, Katowice",
        participant_ids=["usr_ania", "usr_ola", "usr_zuzanna"],
        participant_avatars=[
            USERS["usr_ania"].avatar,
            USERS["usr_ola"].avatar,
            USERS["usr_zuzanna"].avatar,
        ],
        chat_room_id=chat_id,
        created_at=(now - timedelta(minutes=45)).isoformat(),
    )

    CHAT_ROOMS[chat_id] = ChatRoomSchema(
        id=chat_id,
        scope="outing",
        target_id=out_id,
        participant_ids=["usr_ania", "usr_ola", "usr_zuzanna"],
        messages=[
            ChatMessageSchema(
                id="msg_01",
                chat_room_id=chat_id,
                sender_id="usr_ania",
                sender_name="Ania Dąbrowska",
                sender_avatar=USERS["usr_ania"].avatar,
                text="Hej ekipa! Ekipa do Kafej zebrana 🔥 Zarezerwuję nam duży stolik przy oknie!",
                created_at=(now - timedelta(minutes=40)).isoformat(),
                sequence=1,
            ),
            ChatMessageSchema(
                id="msg_02",
                chat_room_id=chat_id,
                sender_id="usr_ola",
                sender_name="Ola Zielińska",
                sender_avatar=USERS["usr_ola"].avatar,
                text="Super! Będę z laptopem punktualnie o 14:00.",
                created_at=(now - timedelta(minutes=30)).isoformat(),
                sequence=2,
            ),
        ],
        created_at=(now - timedelta(minutes=45)).isoformat(),
    )

    t1_chat_id = "chat_trip_makro_01"
    CHAT_ROOMS[t1_chat_id] = ChatRoomSchema(
        id=t1_chat_id,
        scope="trip",
        target_id=t1_id,
        participant_ids=["usr_jakub", "usr_zuzanna"],
        messages=[
            ChatMessageSchema(
                id="msg_trip_01",
                chat_room_id=t1_chat_id,
                sender_id="usr_jakub",
                sender_name="Jakub Kamiński",
                sender_avatar=USERS["usr_jakub"].avatar,
                text="Cześć Zuzanna! Będę przy wejściu głównym za 10 minut.",
                created_at=(now - timedelta(minutes=5)).isoformat(),
                sequence=1,
            )
        ],
        created_at=(now - timedelta(minutes=10)).isoformat(),
    )

    HOTSPOTS["spot_ikea_janki"] = HotspotSpotSchema(
        id="spot_ikea_janki",
        city="Katowice",
        name="IKEA Katowice (Wyjazd Kombi)",
        category=ActivityCategory.HOME,
        emoji="🛋️",
        address="Al. Roździeńskiego 95, Katowice",
        target_time="11:00 (Niedziela)",
        description="Jadę dużym kombi po regał Kallax i klopsiki. Mam 2 wolne miejsca w aucie!",
        cost_policy="Zrzutka na paliwo (15 zł)",
        votes_count=1,
        voter_ids=["usr_marek"],
        voter_avatars=[USERS["usr_marek"].avatar],
        threshold=3,
        group_formed=False,
        created_at=(now - timedelta(hours=5)).isoformat(),
    )


def hydrate_from_storage():
    """
    Hydrates live in-memory stores from SQLite durable storage.
    Ensures that registered users, trips, votes, outings, chat rooms, and pings
    survive application restarts.
    """
    persisted_users = storage.load_users()
    if persisted_users:
        for uid, udata in persisted_users.items():
            USERS[uid] = UserSchema(**udata)

    persisted_hotspots = storage.load_hotspots()
    if persisted_hotspots:
        for hid, hdata in persisted_hotspots.items():
            HOTSPOTS[hid] = HotspotSpotSchema(**hdata)

    persisted_votes = storage.load_hotspot_votes()
    for sid, uid in persisted_votes:
        if sid in HOTSPOTS and uid not in HOTSPOTS[sid].voter_ids:
            HOTSPOTS[sid].voter_ids.append(uid)
            HOTSPOTS[sid].votes_count = len(HOTSPOTS[sid].voter_ids)

    persisted_outings = storage.load_outings()
    for oid, odata in persisted_outings.items():
        OUTINGS[oid] = OutingSchema(**odata)

    persisted_chat_rooms = storage.load_chat_rooms()
    for cid, cdata in persisted_chat_rooms.items():
        CHAT_ROOMS[cid] = ChatRoomSchema(**cdata)

    persisted_trips = storage.load_trips()
    for tid, tdata in persisted_trips.items():
        pin = str(tdata.get("rendezvous_pin", ""))
        if len(pin) != 4 or not pin.isdigit() or (is_production() and pin == "4819"):
            tdata["rendezvous_pin"] = f"{secrets.randbelow(9000) + 1000}"
            storage.persist_trip(tdata)
        if tid == "trip_makro_01":
            if not tdata.get("plan_details"):
                tdata["plan_details"] = PlanDetailsSchema(
                    what="Wspólne zakupy hurtowe Makro Katowice",
                    when="Dzisiaj, 18:30",
                    estimated_duration_minutes=45,
                    cost_policy="split_strictly_50_50",
                    estimated_cost_pln=200.0,
                ).model_dump()
            if not tdata.get("chat_room_id"):
                tdata["chat_room_id"] = "chat_trip_makro_01"
            if not is_production():
                tdata["pin_attempts_left"] = 5
                tdata["rendezvous_verified"] = False
                tdata["status"] = TripStatus.SCHEDULED.value if hasattr(TripStatus.SCHEDULED, "value") else TripStatus.SCHEDULED
                tdata["host_checked_in"] = True
            storage.persist_trip(tdata)
        TRIPS[tid] = TripSchema(**tdata)

    if not is_production() and "chat_trip_makro_01" not in CHAT_ROOMS and "usr_jakub" in USERS:
        CHAT_ROOMS["chat_trip_makro_01"] = ChatRoomSchema(
            id="chat_trip_makro_01",
            scope="trip",
            target_id="trip_makro_01",
            participant_ids=["usr_jakub", "usr_zuzanna"],
            messages=[
                ChatMessageSchema(
                    id="msg_trip_01",
                    chat_room_id="chat_trip_makro_01",
                    sender_id="usr_jakub",
                    sender_name="Jakub Kamiński",
                    sender_avatar=USERS["usr_jakub"].avatar,
                    text="Cześć Zuzanna! Będę przy wejściu głównym za 10 minut.",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    sequence=1,
                )
            ],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    persisted_pings = storage.load_pings()
    now_utc = datetime.now(timezone.utc)
    for pid, pdata in persisted_pings.items():
        if not is_production():
            try:
                exp = datetime.fromisoformat(pdata.get("expires_at", ""))
                if exp <= now_utc and pdata.get("status") == "active":
                    pdata["expires_at"] = (now_utc + timedelta(minutes=45)).isoformat()
                    pdata["remaining_seconds"] = 45 * 60
                    storage.persist_ping(pdata)
            except Exception:
                pass
        PINGS[pid] = LivePingSchema(**pdata)

    persisted_join_requests = storage.load_join_requests()
    for ping_id, requests in persisted_join_requests.items():
        if ping_id not in PINGS:
            continue
        existing = {request.id for request in JOIN_REQUESTS.get(ping_id, [])}
        for request_data in requests:
            if request_data["id"] not in existing:
                JOIN_REQUESTS.setdefault(ping_id, []).append(JoinRequestSchema(**request_data))
                existing.add(request_data["id"])

    persisted_blocks = storage.load_blocks()
    BLOCKED_USERS.clear()
    for blocker, blocked in persisted_blocks:
        BLOCKED_USERS.add((blocker, blocked))

    persisted_reports = storage.load_reports()
    REPORTS.clear()
    for rid, rdata in persisted_reports.items():
        REPORTS[rid] = ReportSchema(**rdata)

    persisted_buddies = storage.load_shopping_buddies()
    SHOPPING_BUDDIES.clear()
    for b in persisted_buddies:
        u1, u2 = b["user_id_1"], b["user_id_2"]
        SHOPPING_BUDDIES.setdefault(u1, []).append(b)
        SHOPPING_BUDDIES.setdefault(u2, []).append(b)


def is_user_blocked(user_a: str, user_b: str) -> bool:
    """
    Returns True if user_a has blocked user_b OR user_b has blocked user_a.
    Protects both parties bidirectionally.
    """
    return (user_a, user_b) in BLOCKED_USERS or (user_b, user_a) in BLOCKED_USERS


def block_user(blocker_id: str, blocked_id: str):
    BLOCKED_USERS.add((blocker_id, blocked_id))
    storage.persist_block(blocker_id, blocked_id)


def unblock_user(blocker_id: str, blocked_id: str):
    BLOCKED_USERS.discard((blocker_id, blocked_id))
    storage.remove_block(blocker_id, blocked_id)


def get_blocked_users_for(user_id: str) -> List[str]:
    return [blocked for (blocker, blocked) in BLOCKED_USERS if blocker == user_id]


def save_report(report: ReportSchema):
    REPORTS[report.id] = report
    storage.persist_report(report.model_dump())


def update_report_status(
    report_id: str,
    status: str,
    resolution_note: Optional[str] = None,
    moderator_id: Optional[str] = None,
):
    if report_id in REPORTS:
        REPORTS[report_id].status = status
        REPORTS[report_id].resolution_note = resolution_note
        REPORTS[report_id].moderator_id = moderator_id
        REPORTS[report_id].updated_at = datetime.now(timezone.utc).isoformat()
    storage.update_report_status(report_id, status, resolution_note, moderator_id)


def save_shopping_buddy(user_1: str, user_2: str):
    storage.persist_shopping_buddy(user_1, user_2)
    buddies = storage.load_shopping_buddies()
    SHOPPING_BUDDIES.clear()
    for b in buddies:
        u1, u2 = b["user_id_1"], b["user_id_2"]
        SHOPPING_BUDDIES.setdefault(u1, []).append(b)
        SHOPPING_BUDDIES.setdefault(u2, []).append(b)


def get_user_shopping_buddies(user_id: str) -> List[dict]:
    return SHOPPING_BUDDIES.get(user_id, [])


def assert_no_unproven_verification_claims(users: Dict[str, dict]) -> None:
    """Until a real provider exists, deployed data may not inherit demo trust flags."""
    proof_flags = (
        "is_id_verified", "is_selfie_verified", "is_background_checked",
        "instagram_verified", "linkedin_verified", "tiktok_verified", "facebook_verified",
    )
    for user_id, record in users.items():
        tier = record.get("trust_tier", TrustTier.BRONZE)
        if tier != TrustTier.BRONZE or any(record.get(flag) for flag in proof_flags):
            raise RuntimeError(
                f"Deployed database contains an unproven verification claim for user {user_id}. "
                "Review and migrate this profile before launch."
            )


def initialize_database():
    existing_users = storage.load_users()
    if is_production():
        if DEMO_USER_IDS.intersection(existing_users):
            raise RuntimeError(
                "Production/staging database contains seeded demo profiles. Use a clean database or perform an explicit reviewed data migration."
            )
        assert_no_unproven_verification_claims(existing_users)
        USERS.clear()
        PINGS.clear()
        JOIN_REQUESTS.clear()
        TRIPS.clear()
        HOTSPOTS.clear()
        OUTINGS.clear()
        CHAT_ROOMS.clear()
        if existing_users:
            hydrate_from_storage()
        return

    seed_initial_data()
    if not existing_users:
        for u in USERS.values():
            storage.persist_user(u.model_dump())
        for p in PINGS.values():
            storage.persist_ping(p.model_dump())
        for t in TRIPS.values():
            storage.persist_trip(t.model_dump())
        for h in HOTSPOTS.values():
            storage.persist_hotspot(h.model_dump())
            for vid in h.voter_ids:
                storage.persist_hotspot_vote(h.id, vid)
        for o in OUTINGS.values():
            storage.persist_outing(o.model_dump())
        for c in CHAT_ROOMS.values():
            storage.persist_chat_room(c.model_dump())
            for m in c.messages:
                storage.persist_chat_message(c.id, m.model_dump())
    else:
        hydrate_from_storage()


initialize_database()
