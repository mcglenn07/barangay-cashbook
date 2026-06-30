"""SQLite data access layer for the barangay cashbook app.

Keeps all SQL in one place and centralizes the running-balance math so the
ledger, the dashboard, and the PDF exporter always agree on the numbers.
"""
import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "cashbook.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Balance computation
# ---------------------------------------------------------------------------
# The cashbook tracks four parallel "funds" per row:
#   Local Treasury : + collection, - deposit (deposit moves cash to the bank)
#   Bank           : + deposit,    - check issued
#   Cash Advance   : + receipt,    - disbursement
#   Petty Cash     : + receipt,    - payment
# Cancelled rows never affect any balance (they exist only to keep the check
# number sequence visible, exactly like the source document's voided checks).

FUND_FIELDS = {
    "lt": ("lt_collection", "lt_deposit"),
    "bank": ("bank_deposit", "bank_check_issued"),
    "ca": ("ca_receipt", "ca_disbursement"),
    "petty": ("petty_receipt", "petty_payment"),
}


def compute_running_balances(opening, transactions):
    """Given opening balances (dict with lt/bank/ca/petty) and a list of
    transaction rows (sqlite3.Row or dict, ordered), return a new list of
    plain dicts, each augmented with lt_balance/bank_balance/ca_balance/
    petty_balance reflecting the balance *after* that row is applied.
    """
    running = dict(opening)
    out = []
    for tx in transactions:
        row = dict(tx)
        if not row.get("is_cancelled"):
            for fund, (in_field, out_field) in FUND_FIELDS.items():
                running[fund] = running[fund] + (row.get(in_field) or 0) - (row.get(out_field) or 0)
        row["lt_balance"] = running["lt"]
        row["bank_balance"] = running["bank"]
        row["ca_balance"] = running["ca"]
        row["petty_balance"] = running["petty"]
        out.append(row)
    return out


def period_totals(transactions):
    totals = {f: 0.0 for pair in FUND_FIELDS.values() for f in pair}
    for tx in transactions:
        if tx.get("is_cancelled"):
            continue
        for field in totals:
            totals[field] += tx.get(field) or 0
    return totals


def get_opening_balances_for_period(conn, period):
    """A period's opening balance is either its own manually-set value
    (used for the very first period of a barangay) or, if an earlier
    period exists, the ending balance of the period immediately before it.
    """
    prev = conn.execute(
        """SELECT id FROM periods
           WHERE barangay_id = ? AND sort_order < ?
           ORDER BY sort_order DESC LIMIT 1""",
        (period["barangay_id"], period["sort_order"]),
    ).fetchone()

    if prev is None:
        return {
            "lt": period["opening_lt_balance"],
            "bank": period["opening_bank_balance"],
            "ca": period["opening_ca_balance"],
            "petty": period["opening_petty_balance"],
        }

    prev_period = conn.execute("SELECT * FROM periods WHERE id = ?", (prev["id"],)).fetchone()
    prev_opening = get_opening_balances_for_period(conn, prev_period)
    prev_txs = conn.execute(
        "SELECT * FROM transactions WHERE period_id = ? ORDER BY sort_order, id",
        (prev_period["id"],),
    ).fetchall()
    prev_rows = compute_running_balances(prev_opening, prev_txs)
    if prev_rows:
        last = prev_rows[-1]
        return {"lt": last["lt_balance"], "bank": last["bank_balance"],
                "ca": last["ca_balance"], "petty": last["petty_balance"]}
    return prev_opening


def get_period_ledger(conn, period_id):
    """Returns (period_row, opening_balances, ledger_rows, totals)."""
    period = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
    if period is None:
        return None, None, None, None
    opening = get_opening_balances_for_period(conn, period)
    txs = conn.execute(
        "SELECT * FROM transactions WHERE period_id = ? ORDER BY sort_order, id",
        (period_id,),
    ).fetchall()
    ledger = compute_running_balances(opening, txs)
    totals = period_totals(ledger)
    return period, opening, ledger, totals
