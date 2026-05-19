import sqlite3
from contextlib import contextmanager

DB_FILE = 'digest_bot.db'


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
        # Create target_chats table
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


def add_target_chat(chat_id, chat_title, last_digest_timestamp=None, last_digest_message_id=None):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE target_chats SET chat_title = ? WHERE chat_id = ?', (chat_title, chat_id))
        if cursor.rowcount == 0:
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
                'UPDATE target_chats SET last_digest_timestamp = ? WHERE chat_id = ?',
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


if __name__ == '__main__':
    init_db()
