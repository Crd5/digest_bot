import sqlite3
import os

DB_FILE = 'digest_bot.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Create target_chats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS target_chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT
        )
    ''')
    # Create state table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_run_timestamp INTEGER
        )
    ''')
    
    # Initialize state if not exists
    cursor.execute('INSERT OR IGNORE INTO state (id, last_run_timestamp) VALUES (1, 0)')
    
    conn.commit()
    conn.close()

def add_target_chat(chat_id, chat_title):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO target_chats (chat_id, chat_title) VALUES (?, ?)', (chat_id, chat_title))
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
    cursor.execute('SELECT chat_id, chat_title FROM target_chats')
    chats = cursor.fetchall()
    conn.close()
    return [{'chat_id': c[0], 'chat_title': c[1]} for c in chats]

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