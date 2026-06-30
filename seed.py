"""Seeds the database with a demo barangay and three consecutive cashbook
periods (July, August, September 2023) transcribed from the uploaded
sample cashbook for Barangay Sta. Rosa Del Sur, Municipality of Pasacao,
Camarines Sur. The three periods are used because their beginning/ending
balances chain together exactly in the source document; an earlier,
non-adjacent September 2022 snippet was also in the source file but is
left out here since it doesn't connect to these three without a gap.

Run with:  python seed.py
"""
from werkzeug.security import generate_password_hash

import db


def run():
    db.init_db()
    with db.db_session() as conn:
        existing = conn.execute("SELECT COUNT(*) c FROM barangays").fetchone()["c"]
        if existing:
            print("Database already has data -- skipping seed. Delete instance/cashbook.db to reseed.")
            return

        cur = conn.execute(
            """INSERT INTO barangays (name, municipality, province, treasurer_name, captain_name)
               VALUES (?,?,?,?,?)""",
            ("Sta. Rosa Del Sur", "Pasacao", "Camarines Sur", "Allan B. Rustia",
             "Hon. Juan D. Santos (sample/placeholder -- update in Barangay Settings)"),
        )
        barangay_id = cur.lastrowid

        conn.execute(
            """INSERT INTO users (barangay_id, username, password_hash, full_name, role)
               VALUES (?,?,?,?,?)""",
            (barangay_id, "treasurer", generate_password_hash("treasurer123", method="pbkdf2:sha256"), "Allan B. Rustia", "treasurer"),
        )
        conn.execute(
            """INSERT INTO users (barangay_id, username, password_hash, full_name, role)
               VALUES (?,?,?,?,?)""",
            (barangay_id, "captain", generate_password_hash("captain123", method="pbkdf2:sha256"), "Hon. Juan D. Santos", "captain"),
        )

        # -------------------------------------------------------------
        # Period 1: July 2023 (first period -> manual opening balances)
        # -------------------------------------------------------------
        cur = conn.execute(
            """INSERT INTO periods (barangay_id, calendar_year, label, start_date, end_date,
               opening_lt_balance, opening_bank_balance, opening_ca_balance, opening_petty_balance,
               certified_by_treasurer, certified_date, sort_order)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (barangay_id, 2023, "July 2023", "2023-07-01", "2023-07-31",
             77437.11, 786331.89, 0, 0, 1, "8/16/2023", 1),
        )
        july_id = cur.lastrowid
        seed_transactions(conn, july_id, JULY_2023)

        # -------------------------------------------------------------
        # Period 2: August 2023 (opening carried forward automatically)
        # -------------------------------------------------------------
        cur = conn.execute(
            """INSERT INTO periods (barangay_id, calendar_year, label, start_date, end_date,
               certified_by_treasurer, certified_date, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            (barangay_id, 2023, "August 2023", "2023-08-01", "2023-08-31", 1, "8/25/2023", 2),
        )
        august_id = cur.lastrowid
        seed_transactions(conn, august_id, AUGUST_2023)

        # -------------------------------------------------------------
        # Period 3: September 2023 (opening carried forward automatically)
        # -------------------------------------------------------------
        cur = conn.execute(
            """INSERT INTO periods (barangay_id, calendar_year, label, start_date, end_date,
               certified_by_treasurer, certified_date, approved_by_captain, approved_date, sort_order)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (barangay_id, 2023, "September 2023", "2023-09-01", "2023-09-29", 1, "9/24/2023", 1, "9/26/2023", 3),
        )
        sept_id = cur.lastrowid
        seed_transactions(conn, sept_id, SEPTEMBER_2023)

    print("Seed complete.")
    print("Log in as treasurer / treasurer123 or captain / captain123")


def seed_transactions(conn, period_id, rows):
    for i, row in enumerate(rows):
        conn.execute(
            """INSERT INTO transactions
               (period_id, entry_date, particulars, reference, check_number, is_cancelled,
                lt_collection, lt_deposit, bank_deposit, bank_check_issued,
                ca_receipt, ca_disbursement, petty_receipt, petty_payment, sort_order)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                period_id, row.get("date", ""), row.get("particulars", ""),
                row.get("reference", ""), row.get("check", ""), 1 if row.get("cancelled") else 0,
                row.get("lt_collection", 0), row.get("lt_deposit", 0),
                row.get("bank_deposit", 0), row.get("bank_check_issued", 0),
                row.get("ca_receipt", 0), row.get("ca_disbursement", 0),
                row.get("petty_receipt", 0), row.get("petty_payment", 0),
                i,
            ),
        )


JULY_2023 = [
    {"date": "Jul 4-26, 2023", "particulars": "Collection", "reference": "RCD No.23-07-001", "lt_collection": 550.00},
    {"date": "7/7/2023", "particulars": "Kalahi BIR Check", "reference": "VDS Check No.23-06-002", "lt_deposit": 1000.00, "bank_deposit": 1000.00},
    {"date": "7/3/2023", "particulars": "NTA", "reference": "RBDCM-23-07-001", "bank_deposit": 395448.00},
    {"date": "", "cancelled": True, "check": "34185604"},
    {"date": "7/4/2023", "particulars": "Payment for referee services during SK basketball Tournament", "check": "34185605", "bank_check_issued": 47215.00},
    {"date": "7/4/2023", "particulars": "Payment for Jersey basketball Uniform", "check": "34185606", "bank_check_issued": 28512.00},
    {"date": "", "cancelled": True, "check": "34185607"},
    {"date": "7/4/2023", "particulars": "Cleanup and Declogging Labor", "check": "34185608", "bank_check_issued": 24010.00, "ca_receipt": 24010.00, "ca_disbursement": 24010.00},
    {"date": "7/6/2023", "particulars": "Cash Advance for Seminar Expenses, Legaspi City", "check": "34185609", "bank_check_issued": 9025.00},
    {"date": "7/6/2023", "particulars": "Cash Advance for Seminar Expenses, Legaspi City", "check": "34185610", "bank_check_issued": 9025.00},
    {"date": "7/6/2023", "particulars": "Cash Advance for Seminar Expenses, Legaspi City", "check": "34185611", "bank_check_issued": 9025.00},
    {"date": "7/14/2023", "particulars": "Payment for water bill", "check": "34185612", "bank_check_issued": 570.36},
    {"date": "7/13/2023", "particulars": "Payment for Electric Bill", "check": "34185613", "bank_check_issued": 2879.47},
    {"date": "7/13/2023", "particulars": "Reimbursement of travel", "check": "34185614", "bank_check_issued": 2970.00},
    {"date": "", "cancelled": True, "check": "34185615"},
    {"date": "", "cancelled": True, "check": "34185616"},
    {"date": "", "cancelled": True, "check": "34185617"},
    {"date": "", "cancelled": True, "check": "34185618"},
    {"date": "", "cancelled": True, "check": "34185619"},
    {"date": "7/13/2023", "particulars": "Payment catering services", "check": "34185620", "bank_check_issued": 28215.00},
    {"date": "7/13/2023", "particulars": "Payment catering services", "check": "34185621", "bank_check_issued": 4750.00},
    {"date": "7/24/2023", "particulars": "Drainage Materials Zone 4", "check": "34185622", "bank_check_issued": 47109.43},
    {"date": "", "cancelled": True, "check": "34185623"},
    {"date": "7/24/2023", "particulars": "Rice purchase for 80 years old above", "check": "34185624", "bank_check_issued": 19008.00},
    {"date": "7/24/2023", "particulars": "Payment for Electric Bill", "check": "34185625", "bank_check_issued": 171.64},
    {"date": "7/24/2023", "particulars": "BHW seminar", "check": "34185626", "bank_check_issued": 660.00},
    {"date": "7/24/2023", "particulars": "BHW seminar", "check": "34185627", "bank_check_issued": 660.00},
    {"date": "7/24/2023", "particulars": "BHW seminar", "check": "34185628", "bank_check_issued": 660.00},
    {"date": "7/24/2023", "particulars": "BHW seminar", "check": "34185629", "bank_check_issued": 660.00},
    {"date": "7/24/2023", "particulars": "BHW seminar", "check": "34185630", "bank_check_issued": 660.00},
    {"date": "7/24/2023", "particulars": "Materials Sports Facilities", "check": "34185631", "bank_check_issued": 20597.13},
    {"date": "7/24/2023", "particulars": "Honorarium July", "check": "34185632", "bank_check_issued": 231555.25, "ca_receipt": 231555.25, "ca_disbursement": 231555.25},
    {"date": "7/24/2023", "particulars": "Labor payroll SK Sports Facilities", "check": "34185633", "bank_check_issued": 7629.30, "ca_receipt": 7629.30, "ca_disbursement": 7629.30},
    {"date": "7/31/2023", "particulars": "Interest", "reference": "RBDCM-23-07-001", "bank_deposit": 193.42},
    {"date": "7/31/2023", "particulars": "Interest Withheld", "reference": "RBDCM-23-07-001", "bank_check_issued": 38.68},
]

AUGUST_2023 = [
    {"date": "Aug 1-29, 2023", "particulars": "Collection", "reference": "RCD No.23-08-001", "lt_collection": 1070.00},
    {"date": "8/1/2023", "particulars": "NTA", "reference": "RBDCM-23-07-001", "bank_deposit": 395448.00},
    {"date": "8/4/2023", "particulars": "Reimbursement of BIR for June 2023", "check": "34185649", "bank_check_issued": 747.43},
    {"date": "8/4/2023", "particulars": "Water Expense for July-Aug. MPH & DCC", "check": "34185635", "bank_check_issued": 570.36},
    {"date": "8/4/2023", "particulars": "Reimbursement of photocopy", "check": "34185636", "bank_check_issued": 998.00},
    {"date": "8/4/2023", "particulars": "Materials for DCC improvement", "check": "34185637", "bank_check_issued": 37175.72},
    {"date": "8/9/2023", "particulars": "Withholding Tax", "check": "34185638", "bank_check_issued": 3214.94},
    {"date": "8/9/2023", "particulars": "Withholding Tax", "check": "34185639", "bank_check_issued": 2952.24},
    {"date": "8/9/2023", "particulars": "Withholding Tax", "check": "34185640", "bank_check_issued": 2802.97},
    {"date": "8/10/2023", "particulars": "Labor Drainage Zone 4", "check": "34185641", "bank_check_issued": 22466.50, "ca_receipt": 22466.50, "ca_disbursement": 22466.50},
    {"date": "8/10/2023", "particulars": "Purchase Printer", "check": "34185642", "bank_check_issued": 14352.00},
    {"date": "8/22/2023", "particulars": "August Honorarium", "check": "34185643", "bank_check_issued": 231555.25, "ca_receipt": 231555.25, "ca_disbursement": 231555.25},
    {"date": "8/24/2023", "particulars": "Rice for PWD", "check": "34185644", "bank_check_issued": 18810.00},
    {"date": "8/24/2023", "particulars": "Rice for Solo Parents", "check": "34185645", "bank_check_issued": 18810.00},
    {"date": "8/24/2023", "particulars": "Snacks for Youth Summit", "check": "34185646", "bank_check_issued": 10830.00},
    {"date": "8/24/2023", "particulars": "Rice for BNS/BHW", "check": "34185647", "bank_check_issued": 9552.00},
    {"date": "8/24/2023", "particulars": "Labor Declogging Coastal Cleanup", "check": "34185648", "bank_check_issued": 38989.60, "ca_receipt": 38989.60, "ca_disbursement": 38989.60},
    {"date": "8/24/2023", "particulars": "Labor of DCC improvement", "check": "34185649b", "bank_check_issued": 10343.90, "ca_receipt": 10343.90, "ca_disbursement": 10343.90},
    {"date": "8/31/2023", "particulars": "Interest", "reference": "RBDCM-23-08-001", "bank_deposit": 191.05},
    {"date": "8/31/2023", "particulars": "Interest Withheld", "reference": "RBDCM-23-08-001", "bank_check_issued": 38.21},
]

SEPTEMBER_2023 = [
    {"date": "Sep 1-29, 2023", "particulars": "Collection", "reference": "RCD No.23-09-001", "lt_collection": 226314.00},
    {"date": "9/1/2023", "particulars": "NTA", "reference": "RBDCM-23-09-001", "bank_deposit": 395448.00},
    {"date": "10/2/2023", "particulars": "Honorarium September", "check": "34185650", "bank_check_issued": 231555.25, "ca_receipt": 231555.25, "ca_disbursement": 231555.25},
    {"date": "10/4/2023", "particulars": "Reimbursement, Withholding Tax Payment", "check": "34185651", "bank_check_issued": 4880.58},
    {"date": "10/3/2023", "particulars": "Payment Electric Expenses, MPH for the Month of Aug", "check": "34185652", "bank_check_issued": 2062.69},
    {"date": "10/4/2023", "particulars": "Payment Water Expenses, DCC for the Month of Sep to Oct", "check": "34185653", "bank_check_issued": 1140.72},
    {"date": "", "cancelled": True, "check": "34185654"},
    {"date": "", "cancelled": True, "check": "34185655"},
    {"date": "10/9/2023", "particulars": "Transfer of Municipal Counterpart for KALAHI CIDSS Project", "check": "34185656", "lt_deposit": 225564.00, "bank_deposit": 225564.00},
    {"date": "9/29/2023", "particulars": "Interest", "reference": "RBDCM-23-08-001", "bank_deposit": 207.96},
    {"date": "9/29/2023", "particulars": "Interest Withheld", "reference": "RBDCM-23-08-001", "bank_check_issued": 41.59},
]


if __name__ == "__main__":
    run()
