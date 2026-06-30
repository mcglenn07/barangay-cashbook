-- Barangay Cashbook schema
-- One SQLite database holds one or more barangays, each with its own
-- treasurer/captain users, periods (monthly cashbook pages) and transactions.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS barangays (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    municipality    TEXT NOT NULL,
    province        TEXT NOT NULL,
    treasurer_name  TEXT NOT NULL DEFAULT '',
    captain_name    TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    barangay_id     INTEGER NOT NULL REFERENCES barangays(id) ON DELETE CASCADE,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('treasurer', 'captain')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A "period" is one cashbook page (the source document groups entries
-- roughly monthly, with a beginning balance carried from the previous
-- period's ending balance).
CREATE TABLE IF NOT EXISTS periods (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    barangay_id             INTEGER NOT NULL REFERENCES barangays(id) ON DELETE CASCADE,
    calendar_year           INTEGER NOT NULL,
    label                   TEXT NOT NULL,           -- e.g. "September 2023"
    start_date              TEXT,                     -- ISO date, optional
    end_date                TEXT,                     -- ISO date, optional
    -- Opening balances. For the very first period of a barangay these are
    -- entered manually; for every later period they are carried forward
    -- automatically from the previous period's computed ending balance.
    opening_lt_balance      REAL NOT NULL DEFAULT 0,
    opening_bank_balance    REAL NOT NULL DEFAULT 0,
    opening_ca_balance      REAL NOT NULL DEFAULT 0,
    opening_petty_balance   REAL NOT NULL DEFAULT 0,
    -- Certification (Treasurer)
    certified_by_treasurer  INTEGER NOT NULL DEFAULT 0,   -- 0/1
    certified_date          TEXT,                          -- text date as printed on the form
    -- Approval (Captain) -- signature-line only, see README; recorded for
    -- audit purposes even though the PDF just prints a blank line to sign.
    approved_by_captain     INTEGER NOT NULL DEFAULT 0,
    approved_date           TEXT,
    sort_order              INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(barangay_id, calendar_year, label)
);

CREATE TABLE IF NOT EXISTS transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id           INTEGER NOT NULL REFERENCES periods(id) ON DELETE CASCADE,
    entry_date          TEXT NOT NULL,         -- free-text as printed (e.g. "10/2/2023" or a date range)
    particulars         TEXT NOT NULL,
    reference            TEXT,                  -- RCD/RBDCM/DV number etc.
    check_number        TEXT,                  -- check no., if any
    is_cancelled        INTEGER NOT NULL DEFAULT 0,  -- voided check row, no amounts

    -- Cash in Local Treasury
    lt_collection       REAL NOT NULL DEFAULT 0,
    lt_deposit          REAL NOT NULL DEFAULT 0,   -- amount moved OUT of local treasury into bank

    -- Cash in Bank
    bank_deposit        REAL NOT NULL DEFAULT 0,   -- amount moved IN from local treasury (or NTA, interest, etc.)
    bank_check_issued   REAL NOT NULL DEFAULT 0,

    -- Cash Advance
    ca_receipt          REAL NOT NULL DEFAULT 0,
    ca_disbursement     REAL NOT NULL DEFAULT 0,

    -- Petty Cash
    petty_receipt       REAL NOT NULL DEFAULT 0,
    petty_payment       REAL NOT NULL DEFAULT 0,

    sort_order          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_transactions_period ON transactions(period_id, sort_order, entry_date);
CREATE INDEX IF NOT EXISTS idx_periods_barangay ON periods(barangay_id, sort_order);
