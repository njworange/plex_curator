import os
import sqlite3


class PlexDbAdapter(object):
    def __init__(self, db_path):
        self.db_path = db_path

    def is_available(self):
        return bool(self.db_path) and os.path.exists(self.db_path)

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _debug(self, debug_callback, message):
        if debug_callback is not None:
            debug_callback(message)

    def list_sections(self):
        if not self.is_available():
            return []
        with self._connect() as con:
            rows = con.execute('SELECT id, name, section_type FROM library_sections ORDER BY name').fetchall()
            return [dict(row) for row in rows]

    def fetch_media_candidates(self, section_filter='', debug_callback=None):
        if not self.is_available():
            self._debug(debug_callback, f'Plex DB unavailable: {self.db_path}')
            return []
        self._debug(debug_callback, f'Plex DB open: {self.db_path}')
        section_values = [x.strip() for x in section_filter.split('|') if x.strip()]
        params = []
        section_sql = ''
        if section_values:
            placeholders = ','.join(['?'] * len(section_values))
            section_sql = f' AND (ls.name IN ({placeholders}) OR CAST(ls.id AS TEXT) IN ({placeholders})) '
            params.extend(section_values)
            params.extend(section_values)
            self._debug(debug_callback, f'Section filter applied: {section_values}')
        else:
            self._debug(debug_callback, 'No section filter applied')

        query = (
            "SELECT "
            "ls.name AS section_name, "
            "ls.section_type AS section_type, "
            "mi.id AS metadata_id, "
            "mi.metadata_type AS metadata_type, "
            "mi.title AS item_title, "
            "mi.`index` AS item_index, "
            "mi.parent_id AS parent_id, "
            "mi.year AS item_year, "
            "parent.`index` AS parent_index, "
            "parent.title AS parent_title, "
            "grand.title AS grandparent_title, "
            "mitem.id AS media_item_id, "
            "mp.id AS media_part_id, "
            "mp.file AS file_path "
            "FROM metadata_items mi "
            "JOIN media_items mitem ON mitem.metadata_item_id = mi.id "
            "JOIN media_parts mp ON mp.media_item_id = mitem.id "
            "LEFT JOIN metadata_items parent ON parent.id = mi.parent_id "
            "LEFT JOIN metadata_items grand ON grand.id = parent.parent_id "
            "LEFT JOIN library_sections ls ON ls.id = COALESCE(mi.library_section_id, parent.library_section_id, grand.library_section_id) "
            "WHERE mi.metadata_type IN (1, 4) "
            "AND mp.file IS NOT NULL "
            f"{section_sql}"
            "ORDER BY ls.name, mp.file"
        )
        with self._connect() as con:
            rows = con.execute(query, params).fetchall()
            self._debug(debug_callback, f'Fetched candidate rows: {len(rows)}')
            return [dict(row) for row in rows]
