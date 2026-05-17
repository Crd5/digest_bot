import sqlite3

DB_FILE = 'digest_bot.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
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

    # Create state table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_run_timestamp INTEGER
        )
    ''')
    
    # Initialize state if not exists
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
    
    conn.commit()
    conn.close()

def add_target_chat(chat_id, chat_title):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE target_chats SET chat_title = ? WHERE chat_id = ?', (chat_title, chat_id))
    if cursor.rowcount == 0:
        cursor.execute('INSERT INTO target_chats (chat_id, chat_title) VALUES (?, ?)', (chat_id, chat_title))
    conn.commit()
    conn.close()

def remove_target_chat(chat_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM target_chats WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

def get_target_chats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, chat_title, last_digest_timestamp FROM target_chats ORDER BY chat_title COLLATE NOCASE')
    chats = cursor.fetchall()
    conn.close()
    return [{'chat_id': c[0], 'chat_title': c[1], 'last_digest_timestamp': c[2]} for c in chats]

def update_chat_last_digest_timestamp(chat_id, timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE target_chats SET last_digest_timestamp = ? WHERE chat_id = ?',
        (timestamp, chat_id),
    )
    conn.commit()
    conn.close()

def get_last_run_timestamp():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT last_run_timestamp FROM state WHERE id = 1')
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def update_last_run_timestamp(timestamp):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE state SET last_run_timestamp = ? WHERE id = 1', (timestamp,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
