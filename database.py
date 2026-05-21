import re
import sqlite3
import time
from contextlib import contextmanager

DB_FILE = 'digest_bot.db'
DEFAULT_SEARCH_LIMIT = 10


@contextmanager
def db_connection():
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS target_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                last_digest_timestamp INTEGER NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute('PRAGMA table_info(target_chats)')
        columns = {row[1] for row in cursor.fetchall()}
        added_chat_cursor = False
        if 'last_digest_timestamp' not in columns:
            cursor.execute('ALTER TABLE target_chats ADD COLUMN last_digest_timestamp INTEGER NOT NULL DEFAULT 0')
            added_chat_cursor = True
        if 'last_digest_message_id' not in columns:
            cursor.execute('ALTER TABLE target_chats ADD COLUMN last_digest_message_id INTEGER NOT NULL DEFAULT 0')

        # Create state table for migrating older databases that used a global cursor.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_run_timestamp INTEGER
            )
        ''')

        cursor.execute('INSERT OR IGNORE INTO state (id, last_run_timestamp) VALUES (1, 0)')
        if added_chat_cursor:
            cursor.execute('SELECT last_run_timestamp FROM state WHERE id = 1')
            res = cursor.fetchone()
            previous_global_cursor = res[0] if res else 0
            if previous_global_cursor > 0:
                cursor.execute(
                    'UPDATE target_chats SET last_digest_timestamp = ? WHERE last_digest_timestamp = 0',
                    (previous_global_cursor,),
                )

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indexed_messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                chat_title TEXT NOT NULL,
                message_timestamp INTEGER NOT NULL,
                sender_name TEXT NOT NULL,
                text TEXT NOT NULL,
                indexed_at_timestamp INTEGER NOT NULL,
                PRIMARY KEY (chat_id, message_id)
            )
        ''')
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS indexed_messages_fts USING fts5(
                chat_title,
                sender_name,
                text,
                chat_id UNINDEXED,
                message_id UNINDEXED,
                message_timestamp UNINDEXED
            )
        ''')


def add_target_chat(chat_id, chat_title, last_digest_timestamp=None, last_digest_message_id=None):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE target_chats SET chat_title = ? WHERE chat_id = ?', (chat_title, chat_id))
        if cursor.rowcount:
            cursor.execute(
                'UPDATE indexed_messages SET chat_title = ? WHERE chat_id = ?',
                (chat_title, chat_id),
            )
            cursor.execute(
                '''
                UPDATE indexed_messages_fts
                SET chat_title = ?
                WHERE rowid IN (
                    SELECT rowid FROM indexed_messages WHERE chat_id = ?
                )
                ''',
                (chat_title, chat_id),
            )
        else:
            cursor.execute(
                '''
                INSERT INTO target_chats (chat_id, chat_title, last_digest_timestamp, last_digest_message_id)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    chat_id,
                    chat_title,
                    last_digest_timestamp or 0,
                    last_digest_message_id or 0,
                ),
            )


def remove_target_chat(chat_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            DELETE FROM indexed_messages_fts
            WHERE rowid IN (
                SELECT rowid FROM indexed_messages WHERE chat_id = ?
            )
            ''',
            (chat_id,),
        )
        cursor.execute('DELETE FROM indexed_messages WHERE chat_id = ?', (chat_id,))
        cursor.execute('DELETE FROM target_chats WHERE chat_id = ?', (chat_id,))


def get_target_chats():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT chat_id, chat_title, last_digest_timestamp, last_digest_message_id
            FROM target_chats
            ORDER BY chat_title COLLATE NOCASE
        ''')
        chats = cursor.fetchall()
    return [
        {
            'chat_id': c[0],
            'chat_title': c[1],
            'last_digest_timestamp': c[2],
            'last_digest_message_id': c[3],
        }
        for c in chats
    ]


def update_chat_last_digest_timestamp(chat_id, timestamp, message_id=None):
    with db_connection() as conn:
        cursor = conn.cursor()
        if message_id is None:
            cursor.execute(
                '''
                UPDATE target_chats
                SET last_digest_timestamp = ?, last_digest_message_id = 0
                WHERE chat_id = ?
                ''',
                (timestamp, chat_id),
            )
        else:
            cursor.execute(
                '''
                UPDATE target_chats
                SET last_digest_timestamp = ?, last_digest_message_id = ?
                WHERE chat_id = ?
                ''',
                (timestamp, message_id, chat_id),
            )


def _message_row(record, indexed_at_timestamp):
    return (
        int(record["chat_id"]),
        int(record["message_id"]),
        record["chat_title"],
        int(record["message_timestamp"]),
        record.get("sender_name") or "Unknown",
        record["text"],
        int(indexed_at_timestamp),
    )


def insert_indexed_messages(records, indexed_at_timestamp=None):
    indexed_at = int(indexed_at_timestamp or time.time())
    inserted = 0
    with db_connection() as conn:
        cursor = conn.cursor()
        for record in records:
            row = _message_row(record, indexed_at)
            cursor.execute(
                '''
                INSERT OR IGNORE INTO indexed_messages (
                    chat_id,
                    message_id,
                    chat_title,
                    message_timestamp,
                    sender_name,
                    text,
                    indexed_at_timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                row,
            )
            if cursor.rowcount:
                inserted += 1
                cursor.execute(
                    '''
                    INSERT INTO indexed_messages_fts (
                        rowid,
                        chat_title,
                        sender_name,
                        text,
                        chat_id,
                        message_id,
                        message_timestamp
                    )
                    SELECT
                        rowid,
                        chat_title,
                        sender_name,
                        text,
                        chat_id,
                        message_id,
                        message_timestamp
                    FROM indexed_messages
                    WHERE chat_id = ? AND message_id = ?
                    ''',
                    (record["chat_id"], record["message_id"]),
                )
    return inserted


def _dict_from_index_row(row):
    return {
        "chat_id": row[0],
        "message_id": row[1],
        "chat_title": row[2],
        "message_timestamp": row[3],
        "sender_name": row[4],
        "text": row[5],
        "indexed_at_timestamp": row[6],
    }


def _fts_query(query):
    terms = re.findall(r"[\w]+", query, flags=re.UNICODE)
    if not terms:
        return ""
    return " OR ".join(f'"{term}"' for term in terms)


def search_indexed_messages(query, limit=DEFAULT_SEARCH_LIMIT):
    match_query = _fts_query(query)
    if not match_query:
        return []
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT
                m.chat_id,
                m.message_id,
                m.chat_title,
                m.message_timestamp,
                m.sender_name,
                m.text,
                m.indexed_at_timestamp
            FROM indexed_messages_fts f
            JOIN indexed_messages m ON m.rowid = f.rowid
            JOIN target_chats t ON t.chat_id = m.chat_id
            WHERE indexed_messages_fts MATCH ?
            ORDER BY bm25(indexed_messages_fts), m.message_timestamp DESC
            LIMIT ?
            ''',
            (match_query, int(limit)),
        )
        rows = cursor.fetchall()
    return [_dict_from_index_row(row) for row in rows]


def get_indexed_messages_since(since_timestamp, limit=200):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT
                limited.chat_id,
                limited.message_id,
                limited.chat_title,
                limited.message_timestamp,
                limited.sender_name,
                limited.text,
                limited.indexed_at_timestamp
            FROM (
                SELECT
                    m.chat_id,
                    m.message_id,
                    m.chat_title,
                    m.message_timestamp,
                    m.sender_name,
                    m.text,
                    m.indexed_at_timestamp
                FROM indexed_messages m
                JOIN target_chats t ON t.chat_id = m.chat_id
                WHERE m.message_timestamp >= ?
                ORDER BY m.message_timestamp DESC, m.chat_id DESC, m.message_id DESC
                LIMIT ?
            ) limited
            ORDER BY limited.message_timestamp ASC, limited.chat_id ASC, limited.message_id ASC
            ''',
            (int(since_timestamp), int(limit)),
        )
        rows = cursor.fetchall()
    return [_dict_from_index_row(row) for row in rows]


if __name__ == '__main__':
    init_db()
