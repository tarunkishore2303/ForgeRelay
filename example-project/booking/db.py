import sqlite3
from contextlib import contextmanager

SCHEMA = '''
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity>0),
 unit_price INTEGER NOT NULL CHECK(unit_price>=0), starts_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reservations (
 id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), customer_id TEXT NOT NULL,
 seats INTEGER NOT NULL CHECK(seats>0), total INTEGER NOT NULL CHECK(total>=0),
 status TEXT NOT NULL CHECK(status IN ('confirmed','cancelled')), created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS reservations_event_status ON reservations(event_id,status);
CREATE TABLE IF NOT EXISTS audit (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, entity_id TEXT NOT NULL,
 payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS booking_requests (
 request_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
 reservation_id TEXT NOT NULL REFERENCES reservations(id));
CREATE TABLE IF NOT EXISTS waitlist (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL REFERENCES events(id),
 customer_id TEXT NOT NULL, seats INTEGER NOT NULL CHECK(seats BETWEEN 1 AND 20),
 status TEXT NOT NULL CHECK(status IN ('waiting','promoted','withdrawn')),
 reservation_id TEXT REFERENCES reservations(id), created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS waitlist_active_customer ON waitlist(event_id,customer_id) WHERE status='waiting';
'''

class Database:
    def __init__(self, path):
        self.path = str(path)
        connection = self.connect()
        try:
            connection.executescript(SCHEMA)
        finally:
            connection.close()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=10000')
        return connection

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
