# Spec 0013: Phase 4 Final Audit Closure Blueprint (Features 11–13)

**Status:** Ratified  
**Covers Scope Features:** 11 (`GA`), 12 (`Beta`), 13 (`GA`) — closing the remaining acceptance criteria of reopened Features 8, 9, and 10.

---

## 1. Honest Audit Ledger (Post-`4a2a1c8` Reality Check)

| Area | Status at `4a2a1c8` | Remaining Gap Closed in Phase 4 |
| :--- | :--- | :--- |
| **Voice Rating Validation & `0012` `STRICT` Schema** | **Fixed for fresh DBs** (`VoiceRatingCreate` `422` validation, `IntegrityError` handling, rate limit, content safety in `backend/main.py:3865-3964`; `STRICT` added to `0012_voice_calls.sql`) | **Feature 11:** Existing `v12` databases created before `4a2a1c8` retain non-`STRICT` `voice_call_sessions` and `voice_call_ratings` tables and require an atomic `v12 -> v13` table-rebuild migration (`m0013_voice_calls_strict_rebuild.py`). |
| **Production TURN Secret Fail-Closed** | **Partial** (`get_ice_servers()` withholds credentials in `backend/voice_manager.py:59-78` and `/api/ready` returns `503` in `backend/main.py:624-628`) | **Feature 11 (closes Feature 8):** Enforce a hard `RuntimeError` startup refusal inside FastAPI `_app_lifespan` (`backend/main.py:131-147`) when `CARTMATE_ENV == "production"` and `CARTMATE_TURN_SECRET` is missing or equals `cartmate_ephemeral_turn_secret_dev`, without breaking non-lifespan module-import tests. |
| **Feed-Level Quorum & WS Hangup-With-Block** | **Fixed** (`PodFeed.tsx:241-282` subscribes at feed level; `main.py:3532-3546` closes both caller and peer sockets; `main.py:120-145` runs 60s pod sweep; `SafetyHub.tsx:151,234` uses `role="alert"` and `tel:112`) | None. |
| **Four-Language (`pl`, `en`, `uk`, `ru`) Localization** | **Partial** (Hero/headers/buttons localized in `PodFeed.tsx` and `VoiceCallHUD.tsx`, but hardcoded Polish remains in `PodFeed.tsx:552,642,652,685,803,835`, `VoiceCallHUD.tsx:611-993`, and `SafetyHub.tsx:75-238` is `pl`/`en`-only) | **Feature 12 (closes Feature 9):** Complete `POD_COPY`, `VOICE_COPY`, and `SAFETY_COPY` across all four locales (`pl`, `en`, `uk`, `ru`) with zero hardcoded Polish or `pl`-only ternaries, backed by automated language-switch tests. |
| **CI Probe, Root `pytest`, & Pod/Voice E2E Journeys** | **Partial** (`.github/workflows/ci.yml:53` and `:107-120` could not be pushed via OAuth token without `workflow` scope; `safety-and-sos.spec.ts` only switches tabs; root `pytest` fails at `ops/test_pilot_preflight.py:203` due to cached `main.CARTMATE_ENV`) | **Feature 13 (closes Feature 10):** Add two-user pod + voice Playwright journeys in `qa/tests/pods-and-voice.spec.ts`, invoke `node qa/codex_mr02_destination_probe.cjs` from `backend/test_voice_calls.py` with `cwd` at repo root, and isolate `ops/test_pilot_preflight.py:203` from cached `main.CARTMATE_ENV`. |

---

## 2. Build Plan & Exact Implementation Design

### Feature 11 · Strict Voice Table Rebuild Migration & Production TURN Startup Guard (`GA`)

#### 11.1 Atomic Python Migration Runner (`v12 -> v13`)
* **Files to create/update:**
  * Create `backend/migrations/0013_voice_calls_strict_rebuild.sql`
  * Create `backend/migrations/m0013_voice_calls_strict_rebuild.py`
  * Update `backend/storage.py` (`MIGRATIONS` list at lines `315-344` and `apply_migrations()` at lines `375-396`)
* **Why SQL-only `executescript` is forbidden:** In SQLite, `PRAGMA foreign_keys = OFF` is a no-op inside an active transaction, and `PRAGMA foreign_key_check` returns rows rather than raising an error unless checked in Python.
* **Exact Runner Design (`m0013_voice_calls_strict_rebuild.py`):**
  1. Follow the exact contract of `backend/migrations/m0011_micro_pods.py`: require `sqlite3.sqlite_version_info >= (3, 37, 0)` and `not conn.in_transaction`.
  2. In `storage.py:apply_migrations()`, when `version == 13`, set `conn.isolation_level = None` before calling `m0013_voice_calls_strict_rebuild.upgrade(conn)` and restore `conn.isolation_level` in `finally:`.
  3. Inside `upgrade(conn)`:
     - Execute `conn.execute("PRAGMA foreign_keys = OFF")` **before** starting the transaction, and verify `conn.execute("PRAGMA foreign_keys").fetchone()[0] == 0`.
     - Execute `conn.execute("BEGIN IMMEDIATE")`.
     - Verify `MAX(version)` in `schema_migrations` is `12`.
     - Record `pre_sessions = conn.execute("SELECT COUNT(*) FROM voice_call_sessions").fetchone()[0]` and `pre_ratings = conn.execute("SELECT COUNT(*) FROM voice_call_ratings").fetchone()[0]`.
     - Execute the statements in `0013_voice_calls_strict_rebuild.sql`:
       1. `CREATE TABLE voice_call_sessions_new (...) STRICT;` (exact schema and `CHECK` constraints of `0012_voice_calls.sql`)
       2. `INSERT INTO voice_call_sessions_new (id, user_a_id, user_b_id, topic, status, started_at, ended_at, duration_seconds, end_reason, created_at) SELECT id, user_a_id, user_b_id, topic, status, started_at, ended_at, duration_seconds, end_reason, created_at FROM voice_call_sessions;`
       3. `CREATE TABLE voice_call_ratings_new (...) STRICT;` (exact schema, `CHECK`, and `UNIQUE (session_id, reporter_id)` constraints of `0012_voice_calls.sql`)
       4. `INSERT INTO voice_call_ratings_new (id, session_id, reporter_id, target_id, rating, report_tag, details, created_at) SELECT id, session_id, reporter_id, target_id, rating, report_tag, details, created_at FROM voice_call_ratings;`
       5. `DROP TABLE voice_call_ratings;`
       6. `DROP TABLE voice_call_sessions;`
       7. `ALTER TABLE voice_call_sessions_new RENAME TO voice_call_sessions;`
       8. `ALTER TABLE voice_call_ratings_new RENAME TO voice_call_ratings;`
       9. Recreate all 4 indexes: `idx_voice_sessions_user_a`, `idx_voice_sessions_user_b`, `idx_voice_sessions_status`, `idx_voice_ratings_target`.
     - Assert `post_sessions == pre_sessions` and `post_ratings == pre_ratings`.
     - Assert `conn.execute("PRAGMA foreign_key_check(voice_call_sessions)").fetchall() == []` and `conn.execute("PRAGMA foreign_key_check(voice_call_ratings)").fetchall() == []`.
     - Assert `"STRICT"` appears in `sqlite_master.sql` for both `voice_call_sessions` and `voice_call_ratings`.
     - Insert `(13, "voice_calls_strict_rebuild", now_iso)` into `schema_migrations`, set `PRAGMA user_version = 13`, and `conn.execute("COMMIT")` (rolling back on any exception).
     - In `finally:`, execute `conn.execute("PRAGMA foreign_keys = ON")`.

#### 11.2 Hard Lifespan Startup Guard for Production TURN Secret
* **Files to update:** `backend/voice_manager.py` (lines `17-78`) and `backend/main.py` (`_app_lifespan` at lines `131-147`).
* **Why lifespan-only (not module import level):** Existing subprocess tests (`backend/test_operator_admission_pilot.py:309-327` and `backend/test_private_pilot_review.py:288-291`) import `main` under `CARTMATE_ENV=production` without entering `with TestClient(main.app):` to test operator activation denial. Putting the guard at module import level would break those tests unless their fixtures are altered.
* **Exact Implementation:**
  - Add `assert_production_turn_secret_configured()` to `VoiceCallManager` in `backend/voice_manager.py`:
    ```python
    def assert_production_turn_secret_configured(self) -> None:
        env = os.getenv("CARTMATE_ENV", CARTMATE_ENV)
        secret = os.getenv("CARTMATE_TURN_SECRET", self.turn_secret)
        if env == "production" and (not secret or secret == DEFAULT_DEV_TURN_SECRET):
            raise RuntimeError(
                "CARTMATE_TURN_SECRET must be configured with a unique non-default secret in production."
            )
    ```
  - Call `voice_call_manager.assert_production_turn_secret_configured()` as the **first line** of `_app_lifespan` in `backend/main.py` (which executes on `uvicorn main:app` startup and on `with TestClient(main.app) as client:`).
* **Tests to add in `backend/test_voice_calls.py`:**
  1. Construct a legacy `v12` SQLite database with non-`STRICT` `voice_call_sessions` and `voice_call_ratings` tables and populated rows, run `DurableStorage(db_path)` / `m0013_voice_calls_strict_rebuild.upgrade(conn)`, and assert row preservation, `STRICT` table definitions, all 4 indexes, `PRAGMA foreign_key_check`, and `PRAGMA foreign_keys == 1` afterward.
  2. Run a subprocess test with `CARTMATE_ENV=production` entering `with TestClient(main.app):` under (a) missing `CARTMATE_TURN_SECRET`, (b) `CARTMATE_TURN_SECRET=cartmate_ephemeral_turn_secret_dev` (both must raise `RuntimeError`), and (c) a custom 32-char secret (must boot cleanly).

---

### Feature 12 · Full Four-Language Localization (`pl`, `en`, `uk`, `ru`) Across Pod, Voice, and Safety Views

* **Files to update:**
  1. `frontend/src/components/PodFeed.tsx`:
     - Replace all remaining hardcoded Polish strings at lines `366-411` (`getTemplateTheme` titles), `435-449` (hero micro-pills `Sprawdzone Third Places`, `Gwarancja Quorum`, `Zero oczekiwanych wydatków`), `502` (`Zamknij powiadomienie`), `525` (empty state subtitle), `552` (`min`), `577-592` (`Zbiórka:`, `Wydatki:`, `Bezpłatnie (0 zł)`, `Płatność za siebie`), `600-635` (`Zajęte miejsca:`, `Wolne:`, `Pełny pod`, `Miejsce X (Zajęte/Wolne)`, `Potrzeba jeszcze...`), `642-657` (`Uczestnicy:`, `Wolne miejsce`), and `719-785` (`Quorum aktywne (X osób)`, `Ty`, `Treść wiadomości`, error fallbacks) with keys in `POD_COPY[lang]`.
  2. `frontend/src/components/VoiceCallHUD.tsx`:
     - Replace all remaining hardcoded Polish strings at lines `611-768` (in-call header `Szyfrowane audio • Bez nagrywania`, `Łączenie rozmówcy...`, `Temat:`, `Limit 10:00`, `Pomysł na temat / pytanie:`, `Inne pytanie`, `Wyłącz wyciszenie`/`Wycisz mikrofon`, `Zakończ rozmowę`/`Koniec`, `Zakończ i Zablokuj`/`Zablokuj`, and block confirm dialog), `780-788` (searching subtitle and `Temat:`), `818-888` (lobby quota labels `Dziś wykorzystano`, `Przerwa po rozmowie`, `Brak (gotowy)`, privacy rules card, topic picker label, default icebreakers, and disabled button states), and `917-993` (rating modal subtitles, `Miła`/`Neutralna`/`Nie na temat`, textarea placeholder, block checkbox label, `Pomiń`, `Zapisz ocenę`) with keys in `VOICE_COPY[lang]`.
  3. `frontend/src/components/SafetyHub.tsx`:
     - Replace every `lang === 'pl' ? ... : ...` binary ternary across lines `75-240` with a four-language `SAFETY_COPY: Record<Language, ...>` dictionary covering `pl`, `en`, `uk`, and `ru`.
* **Automated Verification:**
  - Add an automated test (in `qa/tests/pods-and-voice.spec.ts` or a Node/Playwright check) that switches the header language selector through `PL`, `EN`, `UK`, and `RU` across the `PodFeed`, `VoiceCallHUD`, and `SafetyHub` tabs and asserts localized headings/controls render with zero residual Polish fallback strings in `EN`/`UK`/`RU`.

---

### Feature 13 · End-to-End Pod & Voice Browser Journeys and Root Pytest Isolation (`GA`)

#### 13.1 Dedicated Two-User Playwright Suite (`qa/tests/pods-and-voice.spec.ts`)
* **Files to create/update:**
  * Create `qa/tests/pods-and-voice.spec.ts`
  * Update `qa/playwright.config.ts` if needed to pass Chromium fake media flags: `--use-fake-ui-for-media-stream` and `--use-fake-device-for-media-stream`.
* **Journey 1 — Two-User Pod Quorum Unlock & Live Chat Delivery:**
  1. Seed or locate a `forming` pod at `2/3` confirmed members (or create one via `/api/pods` as `usr_zuzanna` and join as `usr_marek` so it sits at `2/3`).
  2. Open **Browser Context A** (`usr_zuzanna`) on the `Pody 3-5` tab; assert the pod card shows `Formowanie` and `Oczekiwanie na quorum...`.
  3. Open **Browser Context B** (`usr_jakub`) on the `Pody 3-5` tab and click `Dołącz do poda (+1 miejsce)`.
  4. Assert **both Context A and Context B** flip live (without page reload) to `Quorum aktywne!` (`3 / 5`) and enable the `Czat grupy` button.
  5. Open `Czat grupy` (`#pod-chat-drawer-dialog`) in both Context A and Context B. Send `"Cześć grupa, widzimy się przy wejściu!"` from Context B, and assert the message appears live inside **Context A's** open drawer over WebSocket. Press `Escape` in Context A and assert the drawer closes.
* **Journey 2 — Two-User WebRTC Voice Match, Hangup, and Post-Call Rating:**
  1. Ensure the voice call window is open in test/development mode (`CARTMATE_ENV=development` returns `window_open=True` in `voice_manager.py:39`).
  2. Open **Browser Context A** (`usr_zuzanna`) and **Browser Context B** (`usr_marek`) with fake media streams enabled, navigate both to `Głos 10'`, and click `Połącz z kimś teraz (10 min)` in both contexts.
  3. Assert both contexts match via WebSocket (`voice.call_matched`) and transition into the active/connecting call HUD showing the peer's first name and city.
  4. Click the hangup button (`Zakończ rozmowę` / `Koniec`) in Context A, assert `#voice-rating-dialog` opens, select a rating (`Miła`), click `Zapisz ocenę`, and assert the confirmation state (`Dziękujemy za ocenę!`) renders.

#### 13.2 Run `codex_mr02_destination_probe.cjs` Inside `pytest`
* **File to update:** `backend/test_voice_calls.py`
* **Exact Implementation:** Add `test_mr02_destination_probe_subprocess()` using `subprocess.run(["node", "qa/codex_mr02_destination_probe.cjs"], cwd=repo_root, capture_output=True, text=True, check=True)` where `repo_root = Path(__file__).resolve().parent.parent`, parsing the JSON output and asserting `bearerAttached is False` for every call under unapproved origins.

#### 13.3 Fix Root-Level `pytest` Environment Ordering (`ops/test_pilot_preflight.py:203`)
* **File to update:** `ops/test_pilot_preflight.py` (lines `175-207`).
* **Root Cause:** When `pytest` runs from the repository root, `backend/` tests import `config` and `main` first with `CARTMATE_ENV="development"`. When `ops/test_pilot_preflight.py::test_preflight_real_fastapi_app` later sets `monkeypatch.setenv("CARTMATE_ENV", "staging")`, `main.CARTMATE_ENV` and `config.CARTMATE_ENV` are already cached as `"development"`.
* **Exact Fix:** Run the `test_preflight_real_fastapi_app` verification inside a clean Python subprocess (`subprocess.run([sys.executable, "-c", ...])`) with the staging environment variables passed in `env`, so it never collides with or mutates the parent `pytest` process's cached `config` / `main` modules.
