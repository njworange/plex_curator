import json
import os
import sqlite3
from datetime import datetime


DB_FILENAME = 'plex_curator.sqlite3'


def utcnow():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def plugin_root():
    return os.path.dirname(os.path.abspath(__file__))


def get_db_path(custom_path=''):
    if custom_path:
        return custom_path
    return os.path.join(plugin_root(), DB_FILENAME)


def connect(db_path=''):
    con = sqlite3.connect(get_db_path(db_path))
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path=''):
    with connect(db_path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS curator_run (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                plex_db_path TEXT,
                target_sections TEXT,
                summary_json TEXT,
                error_text TEXT
            );

            CREATE TABLE IF NOT EXISTS curator_group (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                media_type TEXT,
                section_name TEXT,
                group_key TEXT NOT NULL,
                candidate_count INTEGER NOT NULL DEFAULT 0,
                winner_candidate_id INTEGER,
                review_status TEXT NOT NULL DEFAULT 'pending',
                rationale TEXT,
                FOREIGN KEY(run_id) REFERENCES curator_run(id)
            );

            CREATE TABLE IF NOT EXISTS curator_candidate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                plex_rating_key INTEGER,
                plex_media_part_id INTEGER,
                media_type TEXT,
                section_name TEXT,
                title TEXT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                release_group TEXT,
                resolution TEXT,
                codec TEXT,
                sources_json TEXT,
                group_key TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                is_winner INTEGER NOT NULL DEFAULT 0,
                planned_action TEXT NOT NULL DEFAULT 'review',
                action_reason TEXT,
                action_status TEXT NOT NULL DEFAULT 'planned',
                metadata_json TEXT,
                FOREIGN KEY(run_id) REFERENCES curator_run(id),
                FOREIGN KEY(group_id) REFERENCES curator_group(id)
            );

            CREATE TABLE IF NOT EXISTS curator_decision (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                run_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                note TEXT,
                payload_json TEXT,
                FOREIGN KEY(run_id) REFERENCES curator_run(id),
                FOREIGN KEY(group_id) REFERENCES curator_group(id)
            );
            """
        )
        _ensure_candidate_columns(con)


def _ensure_candidate_columns(con):
    rows = con.execute('PRAGMA table_info(curator_candidate)').fetchall()
    columns = {row[1] for row in rows}
    if 'planned_action' not in columns:
        con.execute("ALTER TABLE curator_candidate ADD COLUMN planned_action TEXT NOT NULL DEFAULT 'review'")
    if 'action_reason' not in columns:
        con.execute("ALTER TABLE curator_candidate ADD COLUMN action_reason TEXT")
    if 'action_status' not in columns:
        con.execute("ALTER TABLE curator_candidate ADD COLUMN action_status TEXT NOT NULL DEFAULT 'planned'")


def _row_to_dict(row):
    return {key: row[key] for key in row.keys()}


class RunStore(object):
    @staticmethod
    def create(mode, status, plex_db_path='', target_sections='', summary=None, error_text='', db_path=''):
        init_db(db_path)
        with connect(db_path) as con:
            cur = con.execute(
                'INSERT INTO curator_run (created_at, mode, status, plex_db_path, target_sections, summary_json, error_text) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (utcnow(), mode, status, plex_db_path, target_sections, json.dumps(summary or {}, ensure_ascii=True), error_text),
            )
            return cur.lastrowid

    @staticmethod
    def update(run_id, status=None, summary=None, error_text=None, db_path=''):
        init_db(db_path)
        with connect(db_path) as con:
            current = RunStore.get(run_id, db_path=db_path)
            if current is None:
                return
            con.execute(
                'UPDATE curator_run SET status = ?, summary_json = ?, error_text = ? WHERE id = ?',
                (
                    status or current['status'],
                    json.dumps(summary if summary is not None else json.loads(current['summary_json'] or '{}'), ensure_ascii=True),
                    error_text if error_text is not None else current['error_text'],
                    run_id,
                ),
            )

    @staticmethod
    def get(run_id, db_path=''):
        init_db(db_path)
        with connect(db_path) as con:
            row = con.execute('SELECT * FROM curator_run WHERE id = ?', (run_id,)).fetchone()
            return _row_to_dict(row) if row else None

    @staticmethod
    def list_recent(limit=20, db_path=''):
        init_db(db_path)
        with connect(db_path) as con:
            rows = con.execute('SELECT * FROM curator_run ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
            return [_row_to_dict(row) for row in rows]


class GroupStore(object):
    @staticmethod
    def create(run_id, media_type, section_name, group_key, candidate_count, rationale='', db_path=''):
        with connect(db_path) as con:
            cur = con.execute(
                'INSERT INTO curator_group (run_id, created_at, media_type, section_name, group_key, candidate_count, rationale) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (run_id, utcnow(), media_type, section_name, group_key, candidate_count, rationale),
            )
            return cur.lastrowid

    @staticmethod
    def set_winner(group_id, winner_candidate_id, review_status='pending', db_path=''):
        with connect(db_path) as con:
            con.execute(
                'UPDATE curator_group SET winner_candidate_id = ?, review_status = ? WHERE id = ?',
                (winner_candidate_id, review_status, group_id),
            )

    @staticmethod
    def update_review_status(group_id, review_status, rationale='', db_path=''):
        with connect(db_path) as con:
            con.execute(
                'UPDATE curator_group SET review_status = ?, rationale = ? WHERE id = ?',
                (review_status, rationale, group_id),
            )

    @staticmethod
    def list_by_run(run_id, db_path=''):
        with connect(db_path) as con:
            rows = con.execute('SELECT * FROM curator_group WHERE run_id = ? ORDER BY candidate_count DESC, id ASC', (run_id,)).fetchall()
            return [_row_to_dict(row) for row in rows]

    @staticmethod
    def get(group_id, db_path=''):
        with connect(db_path) as con:
            row = con.execute('SELECT * FROM curator_group WHERE id = ?', (group_id,)).fetchone()
            return _row_to_dict(row) if row else None


class CandidateStore(object):
    @staticmethod
    def create(run_id, group_id, candidate, db_path=''):
        with connect(db_path) as con:
            cur = con.execute(
                'INSERT INTO curator_candidate (run_id, group_id, created_at, plex_rating_key, plex_media_part_id, media_type, section_name, title, filename, filepath, release_group, resolution, codec, sources_json, group_key, score, is_winner, planned_action, action_reason, action_status, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    run_id,
                    group_id,
                    utcnow(),
                    candidate.get('plex_rating_key'),
                    candidate.get('plex_media_part_id'),
                    candidate.get('media_type'),
                    candidate.get('section_name'),
                    candidate.get('title'),
                    candidate.get('filename'),
                    candidate.get('filepath'),
                    candidate.get('release_group'),
                    candidate.get('resolution'),
                    candidate.get('codec'),
                    json.dumps(candidate.get('sources', []), ensure_ascii=True),
                    candidate.get('group_key'),
                    candidate.get('score', 0),
                    1 if candidate.get('is_winner') else 0,
                    candidate.get('planned_action', 'review'),
                    candidate.get('action_reason', ''),
                    candidate.get('action_status', 'planned'),
                    json.dumps(candidate.get('metadata', {}), ensure_ascii=True),
                ),
            )
            return cur.lastrowid

    @staticmethod
    def list_by_group(group_id, db_path=''):
        with connect(db_path) as con:
            rows = con.execute('SELECT * FROM curator_candidate WHERE group_id = ? ORDER BY score DESC, id ASC', (group_id,)).fetchall()
            return [_row_to_dict(row) for row in rows]

    @staticmethod
    def update_action(candidate_id, planned_action, action_reason='', action_status='planned', db_path=''):
        with connect(db_path) as con:
            con.execute(
                'UPDATE curator_candidate SET planned_action = ?, action_reason = ?, action_status = ? WHERE id = ?',
                (planned_action, action_reason, action_status, candidate_id),
            )


class DecisionStore(object):
    @staticmethod
    def create(run_id, group_id, action, note='', payload=None, db_path=''):
        with connect(db_path) as con:
            cur = con.execute(
                'INSERT INTO curator_decision (created_at, run_id, group_id, action, note, payload_json) VALUES (?, ?, ?, ?, ?, ?)',
                (utcnow(), run_id, group_id, action, note, json.dumps(payload or {}, ensure_ascii=True)),
            )
            return cur.lastrowid

    @staticmethod
    def list_by_group(group_id, db_path=''):
        with connect(db_path) as con:
            rows = con.execute('SELECT * FROM curator_decision WHERE group_id = ? ORDER BY id DESC', (group_id,)).fetchall()
            return [_row_to_dict(row) for row in rows]
