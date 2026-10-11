CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    article TEXT,
    title TEXT,
    threshold REAL NOT NULL,
    last_price REAL,
    last_checked TEXT,
    fail_count INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    notified_below INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, url)
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    price REAL,
    checked_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tracks_active ON tracks(active);
CREATE INDEX IF NOT EXISTS idx_history_track ON price_history(track_id, checked_at);

CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    html TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
