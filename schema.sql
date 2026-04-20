DROP TABLE IF EXISTS songs;
DROP TABLE IF EXISTS artist_count;
DROP TABLE IF EXISTS songs_count;
DROP TABLE IF EXISTS report;

CREATE TABLE songs (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    artist  TEXT,
    title   TEXT,
    year    TEXT,
    url     TEXT
);

CREATE TABLE artist_count (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    artist      TEXT,
    occurence   INTEGER DEFAULT 0,
    duration    INTEGER DEFAULT 0
);

CREATE TABLE songs_count (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    artist      TEXT,
    occurence   INTEGER DEFAULT 0
);

CREATE TABLE report (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    artist      TEXT,
    url         TEXT,
    duration    INTEGER DEFAULT 0,
    occurence   INTEGER DEFAULT 0
);

CREATE INDEX idx_songs_url       ON songs(url);
CREATE INDEX idx_report_url      ON report(url);
CREATE INDEX idx_report_artist   ON report(artist);
CREATE INDEX idx_report_title    ON report(title);