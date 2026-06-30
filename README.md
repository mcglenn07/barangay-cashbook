# Barangay Cashbook

A role-based web app for managing a Philippine barangay's official cashbook —
built to replicate the real 4-fund ledger format LGU treasurers are required
to keep (Cash in Local Treasury, Cash in Bank, Cash Advance, and Petty Cash),
with PDF export matching the official layout and a two-signature sign-off
(Treasurer certification + Captain approval).

## Why this exists

Most "cashbook" demo apps are a simple list of debits and credits. A real
barangay cashbook isn't — it's four parallel running balances that interact
with each other (a single check can simultaneously post as a Bank
disbursement *and* a Cash Advance receipt/disbursement pair), with balances
that must carry forward exactly from one month to the next, and a paper
trail that ends in two physical signatures. This project models that
faithfully, transcribed from an actual barangay's 2023 cashbook records.

## Features

- **Role-based access** — Treasurer manages everything (settings, periods,
  transactions, certification); Captain has read-only access plus their own
  approval action. Enforced server-side via decorators, not just hidden UI.
- **4-fund parallel ledger** — Local Treasury, Bank, Cash Advance, and Petty
  Cash columns, each with running balances computed from transaction history
  (not stored redundantly, so they can never drift out of sync).
- **Period-to-period balance carry-forward** — each new month's opening
  balance is automatically the prior month's computed ending balance; only
  the very first period for a barangay needs manual opening balances.
- **Cancelled/voided transaction support** — matches how real cashbooks
  record voided checks (kept in the record, excluded from balances).
- **PDF export** — generates a landscape, legal-size PDF matching the
  official cashbook layout, including the two-row fund header, totals row,
  and both signature blocks (Treasurer certification + Captain approval).
- **Pre-loaded demo data** — seeded with three consecutive, balance-chained
  real periods (July–September 2023) transcribed from an actual barangay
  cashbook, so the app is immediately demoable.

## Tech stack

Flask, Jinja2, Werkzeug, SQLite (stdlib `sqlite3`), and ReportLab for PDF
generation — deliberately dependency-light, no JS framework or build step.

## Getting started

```bash
pip install -r requirements.txt
python seed.py      # creates instance/cashbook.db with demo data
python app.py        # runs on http://127.0.0.1:5000
```

### Demo accounts

| Role      | Username    | Password      |
|-----------|-------------|---------------|
| Treasurer | `treasurer` | `treasurer123`|
| Captain   | `captain`   | `captain123`  |

Log in as treasurer to add transactions, create new periods, edit barangay
settings, and certify a period. Log in as captain to view/export periods
read-only and approve a certified period.

To reset to a clean demo state at any point:

```bash
rm -f instance/cashbook.db
python seed.py
```

## Project structure

```
app.py              Flask routes, auth, role decorators
db.py                Data access layer, running-balance computation
schema.sql           SQLite schema (barangays, users, periods, transactions)
pdf_export.py        ReportLab PDF generation
seed.py              Demo data: 1 barangay, 2 users, 3 chained periods
templates/           Jinja2 templates
static/style.css     Hand-written CSS (no external CDN dependency)
```

## The 4-fund ledger model

Each transaction row can post amounts into any combination of these four
fund columns:

- **Cash in Local Treasury** — Collections in / Deposit out
- **Cash in Bank** — Deposit in / Check Issued out
- **Cash Advance** — Receipt in / Disbursement out
- **Petty Cash** — Receipt/Replenishment in / Payments out

For example, an honorarium paid by bank check that was first drawn as a cash
advance posts a Bank "Check Issued" *and* a Cash Advance "Receipt" +
"Disbursement" in the same row — exactly as it appears in the source
records this app was built from.

## A note on scope

This was built as a portfolio project to demonstrate end-to-end product
thinking (real-world domain modeling, role-based auth, server-rendered UI,
PDF generation) rather than as production software for actual LGU use. It
has no encryption at rest, no audit log beyond the certify/approve
timestamps, and SQLite rather than a production database — all reasonable
next steps if this were taken further.
