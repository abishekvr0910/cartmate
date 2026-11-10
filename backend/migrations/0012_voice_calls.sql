-- =============================================================================
-- CartMate migration 0012: 10-Minute Remote Voice Call Engine
-- =============================================================================
-- Additive schema for managing ephemeral 10-minute platonic voice call sessions
-- and deterministic post-call safety evaluations. No audio content is stored.
-- =============================================================================

CREATE TABLE IF NOT EXISTS voice_call_sessions (
    id                TEXT    PRIMARY KEY,
    user_a_id         TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    user_b_id         TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    topic             TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'connecting'
                              CHECK (status IN ('connecting', 'active', 'completed', 'dropped', 'reported', 'cancelled')),
    started_at        TEXT    CHECK (started_at IS NULL OR strftime('%Y-%m-%dT%H:%M:%SZ', started_at) IS started_at),
    ended_at          TEXT    CHECK (ended_at IS NULL OR strftime('%Y-%m-%dT%H:%M:%SZ', ended_at) IS ended_at),
    duration_seconds  INTEGER NOT NULL DEFAULT 0 CHECK (duration_seconds >= 0),
    end_reason        TEXT    CHECK (end_reason IS NULL OR end_reason IN ('timeout_10min', 'user_hangup', 'blocked', 'connection_failed', 'cancelled')),
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                              CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    CHECK (user_a_id <> user_b_id)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_voice_sessions_user_a ON voice_call_sessions (user_a_id, created_at);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_user_b ON voice_call_sessions (user_b_id, created_at);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_status ON voice_call_sessions (status, created_at);

CREATE TABLE IF NOT EXISTS voice_call_ratings (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES voice_call_sessions(id) ON DELETE CASCADE,
    reporter_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    target_id   TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    rating      TEXT NOT NULL CHECK (rating IN ('respectful', 'neutral', 'inappropriate')),
    report_tag  TEXT CHECK (report_tag IS NULL OR report_tag IN ('sexual_misconduct', 'hate_speech', 'harassment', 'commercial_spam', 'other')),
    details     TEXT CHECK (details IS NULL OR length(details) <= 500),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                         CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    UNIQUE (session_id, reporter_id)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_voice_ratings_target ON voice_call_ratings (target_id, rating);
