from decimal import Decimal, InvalidOperation
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash
from psycopg import errors
from .db import connection

bp = Blueprint("main", __name__)

QUERIES_FILE = Path(__file__).resolve().parent.parent / "sql" / "reporting_queries.sql"
REPORTS = ["Q1", "Q2", "Q5", "Q6", "Q7"]

def load_queries():
    """Split sql/reporting_queries.sql into {"Q1": (title, sql), ...}."""
    queries, key = {}, None
    for line in QUERIES_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- Q"):
            key, title = line[3:].split(":", 1)
            queries[key] = [title.strip(), ""]
        elif key:
            queries[key][1] += line + "\n"
    return {k: (t, sql.strip().rstrip(";")) for k, (t, sql) in queries.items()}

@bp.get("/")
def index():
    city = request.args.get("city", "").strip()
    try:
        with connection() as conn:
            stations = conn.execute("""
                SELECT s.station_id, s.name, s.city, s.address,
                       COUNT(p.port_id) AS total_ports,
                       COUNT(p.port_id) FILTER (WHERE p.status='available') AS available_ports
                FROM stations s LEFT JOIN charging_ports p ON p.station_id=s.station_id
                WHERE s.is_active AND (%s='' OR s.city ILIKE %s)
                GROUP BY s.station_id ORDER BY s.name
            """, (city, f"%{city}%")).fetchall()
            cities = [r["city"] for r in conn.execute(
                "SELECT DISTINCT city FROM stations WHERE is_active ORDER BY city").fetchall()]
            summary = conn.execute("""
                SELECT (SELECT COUNT(*) FROM reservations) AS reservations,
                       (SELECT COUNT(*) FROM charging_sessions) AS sessions,
                       (SELECT COALESCE(SUM(total_amount),0) FROM invoices) AS invoiced
            """).fetchone()
            reservations = conn.execute("""
                SELECT r.reservation_id, d.full_name, s.name AS station, cp.port_code,
                       lower(r.reserved_period) AS starts_at, upper(r.reserved_period) AS ends_at, r.status,
                       EXISTS(SELECT 1 FROM charging_sessions cs WHERE cs.reservation_id=r.reservation_id) AS has_session
                FROM reservations r JOIN drivers d USING(driver_id)
                JOIN charging_ports cp USING(port_id) JOIN stations s USING(station_id)
                ORDER BY r.reservation_id DESC LIMIT 15
            """).fetchall()
        return render_template("index.html", stations=stations, summary=summary,
                               reservations=reservations, cities=cities, city=city)
    except Exception as exc:
        return render_template("index.html", stations=[], summary=None, reservations=[],
                               cities=[], city=city, db_error=str(exc))

@bp.post("/reserve")
def reserve():
    try:
        values = (int(request.form["driver_id"]), int(request.form["vehicle_id"]),
                  int(request.form["port_id"]), request.form["starts_at"], request.form["ends_at"])
        with connection() as conn:
            row = conn.execute("""
                INSERT INTO reservations(driver_id,vehicle_id,port_id,reserved_period,status)
                VALUES (%s,%s,%s,tstzrange(%s::timestamptz,%s::timestamptz,'[)'),'confirmed')
                RETURNING reservation_id
            """, values).fetchone()
        flash(f"Reservation #{row['reservation_id']} created.", "success")
    except (ValueError, KeyError):
        flash("Please enter valid IDs and a valid time range.", "error")
    except errors.ExclusionViolation:
        flash("Rejected by PostgreSQL: this port is already booked for an overlapping time.", "error")
    except Exception as exc:
        flash(f"Reservation failed; check IDs, port status and overlapping times. {exc}", "error")
    return redirect(url_for("main.index"))

@bp.post("/reservations/<int:reservation_id>/cancel")
def cancel_reservation(reservation_id):
    with connection() as conn:
        row = conn.execute("""
            UPDATE reservations SET status='cancelled', cancelled_at=now()
            WHERE reservation_id=%s AND status='confirmed' RETURNING reservation_id
        """, (reservation_id,)).fetchone()
    if row:
        flash(f"Reservation #{reservation_id} cancelled.", "success")
    else:
        flash("Only confirmed reservations can be cancelled.", "error")
    return redirect(url_for("main.index"))

@bp.post("/reservations/<int:reservation_id>/delete")
def delete_reservation(reservation_id):
    try:
        with connection() as conn:
            row = conn.execute("""
                DELETE FROM reservations WHERE reservation_id=%s AND status='cancelled'
                RETURNING reservation_id
            """, (reservation_id,)).fetchone()
        if row:
            flash(f"Cancelled reservation #{reservation_id} deleted.", "success")
        else:
            flash("Only cancelled reservations can be deleted.", "error")
    except errors.ForeignKeyViolation:
        flash("Rejected by PostgreSQL: this reservation has a charging session.", "error")
    return redirect(url_for("main.index"))

@bp.get("/sessions")
def sessions():
    with connection() as conn:
        active = conn.execute("""
            SELECT cs.session_id, d.full_name, v.registration_no, s.name AS station, cp.port_code,
                   cs.started_at, cs.start_meter_kwh
            FROM charging_sessions cs JOIN drivers d USING(driver_id) JOIN vehicles v USING(vehicle_id)
            JOIN charging_ports cp USING(port_id) JOIN stations s USING(station_id)
            WHERE cs.status='in_progress' ORDER BY cs.started_at DESC
        """).fetchall()
        invoices = conn.execute("""
            SELECT i.invoice_id, i.session_id, d.full_name, i.energy_kwh, i.total_amount, i.status,
                   i.total_amount-COALESCE(SUM(p.amount) FILTER(WHERE p.status='successful'),0) AS outstanding
            FROM invoices i JOIN charging_sessions cs USING(session_id) JOIN drivers d USING(driver_id)
            LEFT JOIN payments p USING(invoice_id)
            GROUP BY i.invoice_id, d.full_name ORDER BY i.invoice_id DESC LIMIT 15
        """).fetchall()
    return render_template("sessions.html", active=active, invoices=invoices)

@bp.post("/sessions/start")
def start_session():
    try:
        values = (int(request.form["driver_id"]), int(request.form["vehicle_id"]),
                  int(request.form["port_id"]), int(request.form["tariff_id"]),
                  Decimal(request.form["start_meter_kwh"]))
        with connection() as conn:
            row = conn.execute("""
                INSERT INTO charging_sessions(driver_id,vehicle_id,port_id,tariff_id,start_meter_kwh)
                VALUES (%s,%s,%s,%s,%s) RETURNING session_id, started_at, start_meter_kwh
            """, values).fetchone()
            conn.execute("""
                INSERT INTO meter_readings(session_id,recorded_at,meter_kwh,reading_type)
                VALUES (%s,%s,%s,'start')
            """, (row["session_id"], row["started_at"], row["start_meter_kwh"]))
        flash(f"Session #{row['session_id']} started.", "success")
    except (ValueError, KeyError, InvalidOperation):
        flash("Please enter valid IDs and a meter reading.", "error")
    except errors.UniqueViolation:
        flash("Rejected by PostgreSQL: this port already has a session in progress.", "error")
    except Exception as exc:
        flash(f"Session could not be started; check the IDs. {exc}", "error")
    return redirect(url_for("main.sessions"))

@bp.post("/sessions/<int:session_id>/end")
def end_session(session_id):
    try:
        end_meter = Decimal(request.form["end_meter_kwh"])
        # One transaction: close the session, record the end reading, create the invoice.
        with connection() as conn:
            row = conn.execute("""
                WITH done AS (
                 UPDATE charging_sessions SET ended_at=now(), end_meter_kwh=%s, status='completed'
                 WHERE session_id=%s AND status='in_progress'
                 RETURNING session_id, tariff_id, ended_at, end_meter_kwh, end_meter_kwh-start_meter_kwh AS energy_kwh
                ), reading AS (
                 INSERT INTO meter_readings(session_id,recorded_at,meter_kwh,reading_type)
                 SELECT session_id, ended_at, end_meter_kwh, 'end' FROM done
                )
                INSERT INTO invoices(session_id,energy_kwh,price_per_kwh,service_fee)
                SELECT d.session_id, d.energy_kwh, t.price_per_kwh, t.service_fee
                FROM done d JOIN tariffs t USING(tariff_id)
                RETURNING invoice_id, total_amount
            """, (end_meter, session_id)).fetchone()
        if row:
            flash(f"Session #{session_id} completed. Invoice #{row['invoice_id']} for ₹{row['total_amount']}.", "success")
        else:
            flash("Only in-progress sessions can be ended.", "error")
    except (ValueError, KeyError, InvalidOperation):
        flash("Please enter a valid end meter reading.", "error")
    except errors.CheckViolation:
        flash("Rejected by PostgreSQL: end meter reading must be ≥ start reading. Nothing was saved.", "error")
    return redirect(url_for("main.sessions"))

@bp.post("/payments")
def record_payment():
    try:
        invoice_id = int(request.form["invoice_id"])
        amount = Decimal(request.form["amount"])
        method = request.form["payment_method"]
        with connection() as conn:
            inv = conn.execute("""
                SELECT i.total_amount-COALESCE((SELECT SUM(amount) FROM payments
                        WHERE invoice_id=i.invoice_id AND status='successful'),0) AS outstanding
                FROM invoices i WHERE i.invoice_id=%s FOR UPDATE
            """, (invoice_id,)).fetchone()
            if inv is None:
                flash(f"Invoice #{invoice_id} does not exist.", "error")
            elif amount > inv["outstanding"]:
                flash(f"Payment rejected: amount exceeds outstanding balance of ₹{inv['outstanding']}.", "error")
            else:
                conn.execute("""
                    INSERT INTO payments(invoice_id,amount,payment_method,status)
                    VALUES (%s,%s,%s,'successful')
                """, (invoice_id, amount, method))
                status = conn.execute("SELECT status FROM invoices WHERE invoice_id=%s",
                                      (invoice_id,)).fetchone()["status"]
                flash(f"Payment recorded. Invoice #{invoice_id} is now {status}.", "success")
    except (ValueError, KeyError, InvalidOperation):
        flash("Please enter a valid invoice ID and amount.", "error")
    except errors.CheckViolation:
        flash("Rejected by PostgreSQL: amount must be positive and method must be valid.", "error")
    return redirect(url_for("main.sessions"))

@bp.get("/reports")
def reports():
    queries = load_queries()
    results = []
    with connection() as conn:
        for key in REPORTS:
            title, sql = queries[key]
            cur = conn.execute(sql)
            columns = [c.name for c in cur.description]
            results.append((title, columns, cur.fetchall()))
    return render_template("reports.html", results=results)
