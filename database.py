import os
import sqlite3
import unicodedata
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Amharic Fuzzy Normalization
# ---------------------------------------------------------------------------
# Amharic has several letters that are phonetically identical but spelled
# differently. We map all variants to one canonical character so that a
# user's query still matches even if the stored text uses a different variant.
#
# Groups of equivalent characters (one representative chosen per group):
_AMHARIC_EQUIV = {
    # ሀ group  →  ሀ
    'ሃ': 'ሀ', 'ሐ': 'ሀ', 'ሓ': 'ሀ', 'ኃ': 'ሀ', 'ኀ': 'ሀ',
    # አ group  →  አ
    'ዐ': 'አ', 'ዓ': 'አ', 'ኣ': 'አ',
    # ሰ group  →  ሰ
    'ሥ': 'ሰ', 'ሤ': 'ሰ',
    # ጸ group  →  ጸ
    'ፀ': 'ጸ',
    # ዘ group  →  ዘ  (ዛ is a vowel form, kept as-is; only the base homophone)
    # ቀ / ቃ-series identical to ቀ in practice — left alone (different enough)
    # vowel-form normalisation: collapse all vowel-order variants of each
    # base letter down to the first-order (ä) form so partial matches work
    # across ቤ/ቢ/ቦ etc.  We do NOT do this because it would make "ቤ" match
    # "ቢ" which changes meaning — location names must stay distinct.
}

def amharic_normalize(text: str) -> str:
    """Normalize an Amharic string for fuzzy matching.
    
    1. Apply phonetic-equivalence mapping (homophone collapsing).
    2. Strip leading/trailing whitespace and lowercase latin parts.
    """
    if not text:
        return ''
    normalized = []
    for ch in text:
        normalized.append(_AMHARIC_EQUIV.get(ch, ch))
    return ''.join(normalized).strip().lower()

def fuzzy_amharic_match(query: str, target: str) -> bool:
    """Return True if the normalized query is a substring of the normalized target."""
    return amharic_normalize(query) in amharic_normalize(target)

try:
    import psycopg2
    from psycopg2 import extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# Database configuration
# DB_ENGINE: "sqlite" | "postgres" (optional; defaults to postgres when DATABASE_URL is set)
SQLITE_PATH = os.getenv("SQLITE_PATH", "rental_bot.db")
DATABASE_URL = os.getenv("DATABASE_URL")
DB_ENGINE = os.getenv("DB_ENGINE", "").strip().lower()


def use_postgres():
    """Return True when PostgreSQL should be used."""
    if DB_ENGINE == "postgres":
        if not DATABASE_URL:
            raise ValueError("DB_ENGINE=postgres requires DATABASE_URL to be set")
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "DB_ENGINE=postgres but 'psycopg2' is not installed. "
                "Run 'pip install psycopg2-binary'"
            )
        return True
    if DB_ENGINE == "sqlite":
        return False
    # Backward compatible: use PostgreSQL when DATABASE_URL is present
    return bool(DATABASE_URL and POSTGRES_AVAILABLE)


def get_db_backend():
    return "postgres" if use_postgres() else "sqlite"


def _sqlite_connect():
    db_path = os.path.abspath(SQLITE_PATH)
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db_connection():
    if use_postgres():
        # Koyeb/Render sometimes use postgres://, but psycopg2 prefers postgresql://
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url)
    return _sqlite_connect()


def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    is_postgres = use_postgres()
    conn = get_db_connection()
    
    # Handle placeholder difference: Postgres uses %s, SQLite uses ?
    if not is_postgres:
        query = query.replace("%s", "?")
    
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        
        result = None
        if fetchone:
            result = cur.fetchone()
        elif fetchall:
            result = cur.fetchall()
            
        if commit:
            conn.commit()
            
        return result
    finally:
        cur.close()
        conn.close()

def init_db():
    is_postgres = use_postgres()
    # PostgreSQL uses SERIAL for auto-increment, SQLite uses AUTOINCREMENT
    id_type = "SERIAL" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    # Create Users table
    execute_query(f'''
    CREATE TABLE IF NOT EXISTS users (
        id {id_type},
        telegram_id BIGINT UNIQUE,
        username TEXT,
        role TEXT DEFAULT 'user'
    )
    ''', commit=True)
    
    # Create Listings table
    execute_query(f'''
    CREATE TABLE IF NOT EXISTS listings (
        id {id_type},
        owner_id BIGINT,
        title TEXT,
        location TEXT,
        price TEXT,
        photo_file_id TEXT,
        contact_phone TEXT,
        property_purpose TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'pending',
        fee_amount REAL DEFAULT 0,
        transaction_id TEXT,
        last_checked_at TEXT,
        listing_type TEXT DEFAULT 'property',
        channel_notified_at TEXT,
        channel_message_id BIGINT
    )
    ''', commit=True)
    
    # Create Alerts table
    execute_query(f'''
    CREATE TABLE IF NOT EXISTS alerts (
        id {id_type},
        telegram_id BIGINT,
        category TEXT,
        city TEXT,
        neighborhood TEXT,
        property_purpose TEXT,
        created_at TEXT,
        description TEXT
    )
    ''', commit=True)
    
    # Migration handling
    if is_postgres:
        # Postgres migration: ADD COLUMN IF NOT EXISTS
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending'", commit=True)
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS fee_amount REAL DEFAULT 0", commit=True)
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS transaction_id TEXT", commit=True)
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS last_checked_at TEXT", commit=True)
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS listing_type TEXT DEFAULT 'property'", commit=True)
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS property_purpose TEXT", commit=True)
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS channel_notified_at TEXT", commit=True)
        execute_query("ALTER TABLE listings ADD COLUMN IF NOT EXISTS channel_message_id BIGINT", commit=True)
        # Alerts migration
        execute_query("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS description TEXT", commit=True)
    else:
        # SQLite migration
        conn = _sqlite_connect()
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(listings)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'status' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN status TEXT DEFAULT 'pending'")
            if 'fee_amount' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN fee_amount REAL DEFAULT 0")
            if 'transaction_id' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN transaction_id TEXT")
            if 'last_checked_at' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN last_checked_at TEXT")
            if 'listing_type' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN listing_type TEXT DEFAULT 'property'")
            if 'property_purpose' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN property_purpose TEXT")
            if 'channel_notified_at' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN channel_notified_at TEXT")
            if 'channel_message_id' not in columns:
                cursor.execute("ALTER TABLE listings ADD COLUMN channel_message_id BIGINT")
            # Alerts migration
            cursor.execute("PRAGMA table_info(alerts)")
            alert_columns = [col[1] for col in cursor.fetchall()]
            if 'description' not in alert_columns:
                cursor.execute("ALTER TABLE alerts ADD COLUMN description TEXT")
            conn.commit()
        finally:
            conn.close()
    

def add_user(telegram_id, username, role='user'):
    is_postgres = use_postgres()
    if is_postgres:
        query = 'INSERT INTO users (telegram_id, username, role) VALUES (%s, %s, %s) ON CONFLICT (telegram_id) DO NOTHING'
    else:
        query = 'INSERT OR IGNORE INTO users (telegram_id, username, role) VALUES (%s, %s, %s)'
    
    execute_query(query, (telegram_id, username, role), commit=True)

def get_user_role(telegram_id):
    result = execute_query('SELECT role FROM users WHERE telegram_id = %s', (telegram_id,), fetchone=True)
    return result[0] if result else 'user'

def add_listing(owner_id, title, location, price, photo_file_id, contact_phone, fee_amount=0, listing_type='property', property_purpose=None):
    is_postgres = use_postgres()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = '''
    INSERT INTO listings (owner_id, title, location, price, photo_file_id, contact_phone, property_purpose, created_at, status, fee_amount, listing_type)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    if is_postgres:
        query += " RETURNING id"

    params = (owner_id, title, location, price, photo_file_id, contact_phone, property_purpose, created_at, 'pending', fee_amount, listing_type)
    if not is_postgres:
        query = query.replace("%s", "?")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if is_postgres:
            listing_id = cur.fetchone()[0]
        else:
            listing_id = cur.lastrowid
        conn.commit()
        return listing_id
    finally:
        cur.close()
        conn.close()

def update_listing_txid(listing_id, transaction_id):
    execute_query('UPDATE listings SET transaction_id = %s WHERE id = %s', (transaction_id, listing_id), commit=True)

def set_listing_pending(listing_id):
    execute_query('UPDATE listings SET status = %s WHERE id = %s', ('pending', listing_id), commit=True)

def renew_listing(listing_id):
    execute_query('UPDATE listings SET status = %s, transaction_id = NULL WHERE id = %s', ('pending', listing_id), commit=True)

def approve_listing(listing_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_postgres = use_postgres()
    query = 'UPDATE listings SET status = %s, created_at = %s WHERE id = %s AND status != %s'
    params = ('paid', now, listing_id, 'paid')
    if not is_postgres:
        query = query.replace("%s", "?")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        updated_rows = cur.rowcount
        conn.commit()
        return updated_rows > 0
    finally:
        cur.close()
        conn.close()


def is_listing_channel_notified(listing_id):
    result = execute_query('SELECT channel_notified_at FROM listings WHERE id = %s', (listing_id,), fetchone=True)
    return bool(result and result[0])


def reserve_listing_channel_notification(listing_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_postgres = use_postgres()
    query = 'UPDATE listings SET channel_notified_at = %s WHERE id = %s AND channel_notified_at IS NULL'
    params = (now, listing_id)
    if not is_postgres:
        query = query.replace("%s", "?")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close()
        conn.close()


def clear_listing_channel_notification(listing_id):
    is_postgres = use_postgres()
    query = 'UPDATE listings SET channel_notified_at = NULL WHERE id = %s'
    params = (listing_id,)
    if not is_postgres:
        query = query.replace("%s", "?")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close()
        conn.close()


def mark_listing_channel_notified(listing_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_postgres = use_postgres()
    query = 'UPDATE listings SET channel_notified_at = %s WHERE id = %s'
    params = (now, listing_id)
    if not is_postgres:
        query = query.replace("%s", "?")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close()
        conn.close()


def get_listing_by_id(listing_id):
    return execute_query('SELECT * FROM listings WHERE id = %s', (listing_id,), fetchone=True)

def get_pending_listings_with_txid():
    """Returns all listings that have a transaction ID but are still pending."""
    return execute_query("SELECT * FROM listings WHERE status = 'pending' AND transaction_id IS NOT NULL ORDER BY id DESC", fetchall=True)

def get_listing_by_txid(txid):
    """Returns a listing by its transaction ID."""
    return execute_query("SELECT * FROM listings WHERE transaction_id = %s", (txid,), fetchone=True)

def get_all_listings():
    return execute_query("SELECT * FROM listings WHERE status = 'paid' ORDER BY id DESC", fetchall=True)

def _split_location(location):
    """Split stored location into city and neighborhood parts."""
    if not location:
        return '', ''
    if ' - ' in location:
        city, neighborhood = location.split(' - ', 1)
        return city.strip(), neighborhood.strip()
    return location.strip(), ''


def search_listings(query):
    """Search active listings using Amharic-aware fuzzy matching on location and title."""
    all_listings = execute_query("SELECT * FROM listings WHERE status = 'paid' ORDER BY id DESC", fetchall=True)
    if not all_listings:
        return []
    return [row for row in all_listings
            if fuzzy_amharic_match(query, row[3] or '')   # location column
            or fuzzy_amharic_match(query, row[2] or '')]  # title column


def _get_listing_type_value(row):
    """Return the listing type from a DB row, supporting both migrated and fresh schema variations.

    - Migrated SQLite: index 12 = listing_type ('property', 'service', 'looking_for')
    - Fresh schema:   index 13 = listing_type ('property', 'service', 'looking_for')
    """
    if not row:
        return None
    for index in (12, 13, 14, 7, 8):
        if len(row) > index and row[index] in {"property", "service", "looking_for"}:
            return row[index]
    for val in row:
        if isinstance(val, str) and val in {"property", "service", "looking_for"}:
            return val
    return None


def _get_property_purpose_value(row):
    """Return the property purpose from a DB row, supporting both migrated and fresh schema variations.

    - Migrated SQLite: index 13 = property_purpose ('buy', 'sell', 'rent', 'service')
    - Fresh schema:   index 7  = property_purpose ('buy', 'sell', 'rent', 'service')
    """
    if not row:
        return None
    for index in (13, 7, 6, 8, 12, 14):
        if len(row) > index and row[index] in {"buy", "sell", "rent", "service"}:
            return row[index]
    for val in row:
        if isinstance(val, str) and val in {"buy", "sell", "rent", "service"}:
            return val
    return None


def search_listings_by_location(city_query, neighborhood_query=None, listing_type=None, property_purpose=None, category=None):
    """Search active listings by city and optional neighborhood, with optional type/purpose filters.
    
    Listings with NULL listing_type or NULL property_purpose are always included
    (backward-compat for records created before the filtering feature).
    """
    all_listings = execute_query("SELECT * FROM listings WHERE status = 'paid' ORDER BY id DESC", fetchall=True)
    if not all_listings:
        return []

    city_query = (city_query or '').strip()
    neighborhood_query = (neighborhood_query or '').strip() if neighborhood_query else ''

    results = []
    for row in all_listings:
        city, neighborhood = _split_location(row[3] or '')
        city_match = fuzzy_amharic_match(city_query, city) if city_query else True
        if neighborhood_query:
            target = neighborhood or row[3] or ''
            neighborhood_match = fuzzy_amharic_match(neighborhood_query, target)
        else:
            neighborhood_match = True
        if city_match and neighborhood_match:
            results.append(row)

    if listing_type:
        results = [r for r in results if _get_listing_type_value(r) in {None, listing_type}]
    if property_purpose:
        results = [r for r in results if _get_property_purpose_value(r) in {None, property_purpose}]
    if category and category != "ሁሉም":
        results = [r for r in results if fuzzy_amharic_match(category, r[2] or '')]
    return results

def get_listings_by_city(city, listing_type=None, property_purpose=None, category=None):
    """Return active listings in a given city, optionally filtered by listing_type and property_purpose.
    
    Listings with NULL listing_type or NULL property_purpose are always included
    (backward-compat for records created before the filtering feature).
    """
    all_listings = execute_query("SELECT * FROM listings WHERE status = 'paid' ORDER BY id DESC", fetchall=True)
    if not all_listings:
        return []
    results = [row for row in all_listings
               if fuzzy_amharic_match(city, row[3] or '')]  # location column only
    if listing_type:
        results = [r for r in results if _get_listing_type_value(r) in {None, listing_type}]
    if property_purpose:
        results = [r for r in results if _get_property_purpose_value(r) in {None, property_purpose}]
    if category and category != "ሁሉም":
        results = [r for r in results if fuzzy_amharic_match(category, r[2] or '')]
    return results

def expire_old_listings():
    """Mark service listings older than 30 days as expired."""
    is_postgres = use_postgres()
    if is_postgres:
        query = "UPDATE listings SET status = 'expired' WHERE status = 'paid' AND listing_type = 'service' AND created_at::timestamp <= NOW() - INTERVAL '30 days'"
    else:
        query = "UPDATE listings SET status = 'expired' WHERE status = 'paid' AND listing_type = 'service' AND created_at <= date('now', '-30 days')"
    execute_query(query, commit=True)

def get_active_listing_count():
    result = execute_query("SELECT COUNT(*) FROM listings WHERE status = 'paid'", fetchone=True)
    return result[0] if result else 0

def get_pending_listing_count():
    result = execute_query("SELECT COUNT(*) FROM listings WHERE status = 'pending'", fetchone=True)
    return result[0] if result else 0

def get_total_user_count():
    result = execute_query("SELECT COUNT(*) FROM users", fetchone=True)
    return result[0] if result else 0

def get_listings_by_owner(owner_id, listing_type=None, property_purpose=None):
    results = execute_query("SELECT * FROM listings WHERE owner_id = %s ORDER BY id DESC", (owner_id,), fetchall=True)
    if not results:
        return []
    if listing_type:
        results = [r for r in results if _get_listing_type_value(r) in {None, listing_type}]
    if property_purpose:
        results = [r for r in results if _get_property_purpose_value(r) in {None, property_purpose}]
    return results

def delete_listing(listing_id):
    execute_query('DELETE FROM listings WHERE id = %s', (listing_id,), commit=True)

def unlist_listing(listing_id):
    execute_query("UPDATE listings SET status = 'rented' WHERE id = %s", (listing_id,), commit=True)

def set_channel_message_id(listing_id, message_id):
    """Store the Telegram channel message ID for a listing so it can be deleted later."""
    execute_query('UPDATE listings SET channel_message_id = %s WHERE id = %s', (message_id, listing_id), commit=True)

def get_channel_message_id(listing_id):
    """Retrieve the stored channel message ID for a listing."""
    result = execute_query('SELECT channel_message_id FROM listings WHERE id = %s', (listing_id,), fetchone=True)
    return result[0] if result and result[0] else None

def get_all_users():
    return execute_query('SELECT telegram_id, username, role FROM users', fetchall=True)

def get_listings_needing_check(days=14):
    """Find active listings that haven't been checked in more than 'days'."""
    is_postgres = use_postgres()
    if is_postgres:
        # Postgres uses INTERVAL
        query = """
        SELECT * FROM listings 
        WHERE status = 'paid' 
        AND (last_checked_at IS NULL OR last_checked_at::timestamp <= NOW() - INTERVAL %s)
        """
        interval = f'{days} days'
        return execute_query(query, (interval,), fetchall=True)
    else:
        # SQLite uses date()
        query = f"SELECT * FROM listings WHERE status = 'paid' AND (last_checked_at IS NULL OR last_checked_at <= date('now', '-{days} days'))"
        return execute_query(query, fetchall=True)

def update_last_checked(listing_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query("UPDATE listings SET last_checked_at = %s WHERE id = %s", (now, listing_id), commit=True)

def refresh_listing_date(listing_id):
    """Updates the created_at date to now, resetting the 60-day expiry clock."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query("UPDATE listings SET created_at = %s WHERE id = %s", (now, listing_id), commit=True)

# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
def add_alert(telegram_id, category, city, neighborhood, property_purpose, description=None):
    is_postgres = use_postgres()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = '''
    INSERT INTO alerts (telegram_id, category, city, neighborhood, property_purpose, created_at, description)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    '''
    if not is_postgres:
        query = query.replace("%s", "?")
    execute_query(query, (telegram_id, category, city, neighborhood, property_purpose, created_at, description), commit=True)

def get_matching_alerts(category, location, property_purpose):
    city, neighborhood = _split_location(location)
    alerts = execute_query("SELECT * FROM alerts", fetchall=True)
    if not alerts:
        return []
    
    matches = []
    for alert in alerts:
        a_tgid, a_cat, a_city, a_neigh, a_purp = alert[1], alert[2], alert[3], alert[4], alert[5]
        
        if a_purp and a_purp != property_purpose:
            continue
        if a_cat and a_cat != "ሁሉም" and not fuzzy_amharic_match(a_cat, category):
            continue
        if a_city and a_city != "ሁሉም" and not fuzzy_amharic_match(a_city, city):
            continue
        if a_neigh and a_neigh != "ሁሉም" and not fuzzy_amharic_match(a_neigh, neighborhood):
            continue
        
        matches.append(a_tgid)
    return list(set(matches))

def get_alerts_by_user(telegram_id):
    query = "SELECT * FROM alerts WHERE telegram_id = %s"
    if not use_postgres():
        query = query.replace("%s", "?")
    return execute_query(query, (telegram_id,), fetchall=True)

def delete_alert(alert_id, telegram_id):
    query = "DELETE FROM alerts WHERE id = %s AND telegram_id = %s"
    if not use_postgres():
        query = query.replace("%s", "?")
    execute_query(query, (alert_id, telegram_id), commit=True)

