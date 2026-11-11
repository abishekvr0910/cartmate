-- Migration 0015: Durable Pilot Funnel Analytics Store
-- Tracks the 100-person Silesia pilot conversion funnel:
-- signup -> first_pod_view -> pod_join -> quorum_reached -> attend -> repeat
-- Zero PII: only pseudonymous user IDs, event names, sanitized JSON properties, and canonical UTC timestamps.

CREATE TABLE IF NOT EXISTS analytics_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT,
    event_name      TEXT    NOT NULL CHECK (length(event_name) BETWEEN 2 AND 64),
    properties_json TEXT    NOT NULL DEFAULT '{}' CHECK (json_valid(properties_json)),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                            CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_analytics_events_name_time ON analytics_events (event_name, created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_name  ON analytics_events (user_id, event_name);
