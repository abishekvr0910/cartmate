import os
import sqlite3
import pytest
from storage import DurableStorage, get_db_connection

def test_migration_11_on_real_cartmate_schema(tmp_path):
    db_file = str(tmp_path / "test_cartmate_v11.db")
    # Initialize DurableStorage with all migrations (1..11)
    storage = DurableStorage(db_file)
    conn = get_db_connection(db_file)
    
    # Verify tables created
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "activity_templates" in tables
    assert "third_places" in tables
    assert "third_place_templates" in tables
    assert "cohorts" in tables
    assert "pods" in tables
    assert "pod_members" in tables
    assert "pod_messages" in tables
    
    # Verify templates seeded
    templates = conn.execute("SELECT code, name FROM activity_templates ORDER BY sort_order").fetchall()
    assert len(templates) == 4
    assert [t[0] for t in templates] == ["study_sprint", "park_walk", "board_games", "language_exchange"]
    
    # Insert a real third place
    conn.execute("""
        INSERT INTO third_places (slug, name, kind, city, address, meeting_point, latitude, longitude, is_indoor, verified_at)
        VALUES ('biblioteka-slaska', 'Biblioteka Śląska', 'library', 'Katowice', 'plac Rady Europy 1', 'Główne wejście przy recepcji', 50.252, 19.031, 1, '2026-11-09T00:00:00Z')
    """)
    place_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Link third place to template
    conn.execute("INSERT INTO third_place_templates (third_place_id, template_code) VALUES (?, 'study_sprint')", (place_id,))
    
    # Insert real CartMate users with string IDs
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_zuzanna', 'zuzanna@example.pl', '+48601234567', '{\"name\":\"Zuzanna\"}', '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')
    """)
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_jakub', 'jakub@example.pl', '+48502876543', '{\"name\":\"Jakub\"}', '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')
    """)
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_ania', 'ania@example.pl', '+48791432109', '{\"name\":\"Ania\"}', '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')
    """)
    
    # Create a micro-pod
    conn.execute(f"""
        INSERT INTO pods (template_code, third_place_id, created_by_user_id, language_code, starts_at, ends_at, quorum_deadline_at, min_participants, max_participants, spend_expectation)
        VALUES ('study_sprint', {place_id}, 'usr_zuzanna', 'pl', '2026-11-09T14:00:00Z', '2026-11-09T15:00:00Z', '2026-11-09T13:00:00Z', 3, 5, 'no_expected_spend')
    """)
    pod_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Initially status is 'forming' and count is 0
    pod = conn.execute("SELECT status, confirmed_count FROM pods WHERE id = ?", (pod_id,)).fetchone()
    assert pod[0] == 'forming'
    assert pod[1] == 0
    
    # User 1 joins
    conn.execute("INSERT INTO pod_members (pod_id, user_id) VALUES (?, 'usr_zuzanna')", (pod_id,))
    pod = conn.execute("SELECT status, confirmed_count FROM pods WHERE id = ?", (pod_id,)).fetchone()
    assert pod[0] == 'forming'
    assert pod[1] == 1
    
    # Try sending chat message before quorum -> trigger must abort!
    with pytest.raises(sqlite3.IntegrityError, match="chat_locked_until_quorum"):
        conn.execute("INSERT INTO pod_messages (pod_id, sender_user_id, body) VALUES (?, 'usr_zuzanna', 'Hej!')", (pod_id,))
        
    # User 2 joins
    conn.execute("INSERT INTO pod_members (pod_id, user_id) VALUES (?, 'usr_jakub')", (pod_id,))
    pod = conn.execute("SELECT status, confirmed_count FROM pods WHERE id = ?", (pod_id,)).fetchone()
    assert pod[0] == 'forming'
    assert pod[1] == 2
    
    # User 3 joins -> triggers quorum (3 confirmed members)!
    conn.execute("INSERT INTO pod_members (pod_id, user_id) VALUES (?, 'usr_ania')", (pod_id,))
    pod = conn.execute("SELECT status, confirmed_count FROM pods WHERE id = ?", (pod_id,)).fetchone()
    assert pod[0] == 'quorum'
    assert pod[1] == 3
    
    # Now chat succeeds because quorum is reached!
    conn.execute("INSERT INTO pod_messages (pod_id, sender_user_id, body) VALUES (?, 'usr_zuzanna', 'Cześć wszystkim!')", (pod_id,))
    msg = conn.execute("SELECT body, sender_user_id FROM pod_messages WHERE pod_id = ?", (pod_id,)).fetchone()
    assert msg[0] == 'Cześć wszystkim!'
    assert msg[1] == 'usr_zuzanna'
    
    # User 3 leaves -> drops below quorum -> status automatically reverts to 'forming'!
    conn.execute("UPDATE pod_members SET status = 'left', status_changed_at = '2026-11-09T01:00:00Z' WHERE pod_id = ? AND user_id = 'usr_ania'", (pod_id,))
    pod = conn.execute("SELECT status, confirmed_count FROM pods WHERE id = ?", (pod_id,)).fetchone()
    assert pod[0] == 'forming'
    assert pod[1] == 2
    
    # Chat locks again because pod dropped below quorum!
    with pytest.raises(sqlite3.IntegrityError, match="chat_locked_until_quorum"):
        conn.execute("INSERT INTO pod_messages (pod_id, sender_user_id, body) VALUES (?, 'usr_zuzanna', 'Ktoś jeszcze dojdzie?')", (pod_id,))
    
    conn.close()
