import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_file, g
from werkzeug.security import check_password_hash

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def ensure_db():
    if not os.path.exists(db.DB_PATH):
        db.init_db()


@app.before_request
def load_logged_in_user():
    ensure_db()
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        with db.db_session() as conn:
            row = conn.execute(
                "SELECT u.*, b.name AS barangay_name, b.municipality, b.province, "
                "b.treasurer_name, b.captain_name FROM users u "
                "JOIN barangays b ON b.id = u.barangay_id WHERE u.id = ?",
                (user_id,),
            ).fetchone()
            g.user = dict(row) if row else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("login", next=request.path))
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_user():
    return {"current_user": g.get("user")}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db.db_session() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None or not check_password_hash(row["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")
        session.clear()
        session["user_id"] = row["id"]
        flash(f"Welcome, {row['full_name']}.", "success")
        next_url = request.args.get("next") or url_for("dashboard")
        return redirect(next_url)
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    with db.db_session() as conn:
        barangay = conn.execute("SELECT * FROM barangays WHERE id = ?", (g.user["barangay_id"],)).fetchone()
        periods = conn.execute(
            "SELECT * FROM periods WHERE barangay_id = ? ORDER BY sort_order DESC",
            (g.user["barangay_id"],),
        ).fetchall()
        period_summaries = []
        for p in periods:
            _, opening, ledger, totals = db.get_period_ledger(conn, p["id"])
            ending = ledger[-1] if ledger else {
                "lt_balance": opening["lt"], "bank_balance": opening["bank"],
                "ca_balance": opening["ca"], "petty_balance": opening["petty"],
            }
            period_summaries.append({"period": dict(p), "ending": ending, "tx_count": len(ledger)})
    return render_template("dashboard.html", barangay=dict(barangay), period_summaries=period_summaries)


# ---------------------------------------------------------------------------
# Barangay settings (treasurer only)
# ---------------------------------------------------------------------------
@app.route("/settings", methods=["GET", "POST"])
@role_required("treasurer")
def settings():
    with db.db_session() as conn:
        barangay = conn.execute("SELECT * FROM barangays WHERE id = ?", (g.user["barangay_id"],)).fetchone()
        if request.method == "POST":
            conn.execute(
                """UPDATE barangays SET name=?, municipality=?, province=?,
                   treasurer_name=?, captain_name=? WHERE id=?""",
                (
                    request.form["name"].strip(),
                    request.form["municipality"].strip(),
                    request.form["province"].strip(),
                    request.form["treasurer_name"].strip(),
                    request.form["captain_name"].strip(),
                    g.user["barangay_id"],
                ),
            )
            flash("Barangay details updated.", "success")
            return redirect(url_for("settings"))
    return render_template("settings.html", barangay=dict(barangay))


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------
@app.route("/periods/new", methods=["GET", "POST"])
@role_required("treasurer")
def new_period():
    with db.db_session() as conn:
        has_existing = conn.execute(
            "SELECT COUNT(*) AS c FROM periods WHERE barangay_id = ?", (g.user["barangay_id"],)
        ).fetchone()["c"]
        if request.method == "POST":
            max_sort = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) AS m FROM periods WHERE barangay_id = ?",
                (g.user["barangay_id"],),
            ).fetchone()["m"]

            def f(name):
                val = request.form.get(name, "").replace(",", "").strip()
                return float(val) if val else 0.0

            conn.execute(
                """INSERT INTO periods
                   (barangay_id, calendar_year, label, start_date, end_date,
                    opening_lt_balance, opening_bank_balance, opening_ca_balance, opening_petty_balance,
                    sort_order)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    g.user["barangay_id"],
                    int(request.form["calendar_year"]),
                    request.form["label"].strip(),
                    request.form.get("start_date") or None,
                    request.form.get("end_date") or None,
                    f("opening_lt_balance") if not has_existing else 0,
                    f("opening_bank_balance") if not has_existing else 0,
                    f("opening_ca_balance") if not has_existing else 0,
                    f("opening_petty_balance") if not has_existing else 0,
                    max_sort + 1,
                ),
            )
            flash("Period created.", "success")
            return redirect(url_for("dashboard"))
    return render_template("new_period.html", has_existing=has_existing)


@app.route("/periods/<int:period_id>")
@login_required
def view_period(period_id):
    with db.db_session() as conn:
        period = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
        if period is None or period["barangay_id"] != g.user["barangay_id"]:
            abort(404)
        barangay = conn.execute("SELECT * FROM barangays WHERE id = ?", (period["barangay_id"],)).fetchone()
        _, opening, ledger, totals = db.get_period_ledger(conn, period_id)
    return render_template(
        "period.html",
        period=dict(period),
        barangay=dict(barangay),
        opening=opening,
        ledger=ledger,
        totals=totals,
    )


@app.route("/periods/<int:period_id>/transactions/new", methods=["POST"])
@role_required("treasurer")
def add_transaction(period_id):
    with db.db_session() as conn:
        period = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
        if period is None or period["barangay_id"] != g.user["barangay_id"]:
            abort(404)

        def f(name):
            val = request.form.get(name, "").replace(",", "").strip()
            return float(val) if val else 0.0

        max_sort = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) AS m FROM transactions WHERE period_id = ?",
            (period_id,),
        ).fetchone()["m"]

        is_cancelled = 1 if request.form.get("is_cancelled") == "on" else 0

        conn.execute(
            """INSERT INTO transactions
               (period_id, entry_date, particulars, reference, check_number, is_cancelled,
                lt_collection, lt_deposit, bank_deposit, bank_check_issued,
                ca_receipt, ca_disbursement, petty_receipt, petty_payment, sort_order)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                period_id,
                request.form.get("entry_date", "").strip(),
                request.form.get("particulars", "").strip() or ("CANCELLED" if is_cancelled else ""),
                request.form.get("reference", "").strip(),
                request.form.get("check_number", "").strip(),
                is_cancelled,
                f("lt_collection"), f("lt_deposit"),
                f("bank_deposit"), f("bank_check_issued"),
                f("ca_receipt"), f("ca_disbursement"),
                f("petty_receipt"), f("petty_payment"),
                max_sort + 1,
            ),
        )
    flash("Transaction added.", "success")
    return redirect(url_for("view_period", period_id=period_id))


@app.route("/periods/<int:period_id>/transactions/<int:tx_id>/delete", methods=["POST"])
@role_required("treasurer")
def delete_transaction(period_id, tx_id):
    with db.db_session() as conn:
        period = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
        if period is None or period["barangay_id"] != g.user["barangay_id"]:
            abort(404)
        conn.execute("DELETE FROM transactions WHERE id = ? AND period_id = ?", (tx_id, period_id))
    flash("Transaction removed.", "success")
    return redirect(url_for("view_period", period_id=period_id))


@app.route("/periods/<int:period_id>/certify", methods=["POST"])
@role_required("treasurer")
def certify_period(period_id):
    with db.db_session() as conn:
        period = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
        if period is None or period["barangay_id"] != g.user["barangay_id"]:
            abort(404)
        conn.execute(
            "UPDATE periods SET certified_by_treasurer = 1, certified_date = ? WHERE id = ?",
            (request.form.get("certified_date", "").strip(), period_id),
        )
    flash("Period certified by treasurer.", "success")
    return redirect(url_for("view_period", period_id=period_id))


@app.route("/periods/<int:period_id>/approve", methods=["POST"])
@role_required("captain")
def approve_period(period_id):
    with db.db_session() as conn:
        period = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
        if period is None or period["barangay_id"] != g.user["barangay_id"]:
            abort(404)
        conn.execute(
            "UPDATE periods SET approved_by_captain = 1, approved_date = ? WHERE id = ?",
            (request.form.get("approved_date", "").strip(), period_id),
        )
    flash("Period noted/approved by captain.", "success")
    return redirect(url_for("view_period", period_id=period_id))


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------
@app.route("/periods/<int:period_id>/export.pdf")
@login_required
def export_period_pdf(period_id):
    from pdf_export import build_period_pdf

    with db.db_session() as conn:
        period = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
        if period is None or period["barangay_id"] != g.user["barangay_id"]:
            abort(404)
        barangay = conn.execute("SELECT * FROM barangays WHERE id = ?", (period["barangay_id"],)).fetchone()
        _, opening, ledger, totals = db.get_period_ledger(conn, period_id)

    buf = build_period_pdf(dict(barangay), dict(period), opening, ledger, totals)
    filename = f"cashbook_{dict(barangay)['name'].replace(' ', '_')}_{dict(period)['label'].replace(' ', '_')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


if __name__ == "__main__":
    ensure_db()
    app.run(debug=True, host="0.0.0.0", port=5001)
