from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import connection

bp = Blueprint("main", __name__)

@bp.get("/")
def index():
    try:
        with connection() as conn:
            stations = conn.execute("""
                SELECT s.station_id, s.name, s.city, s.address,
                       COUNT(p.port_id) AS total_ports,
                       COUNT(p.port_id) FILTER (WHERE p.status='available') AS available_ports
                FROM stations s LEFT JOIN charging_ports p ON p.station_id=s.station_id
                WHERE s.is_active
                GROUP BY s.station_id ORDER BY s.name
            """).fetchall()
            summary = conn.execute("""
                SELECT (SELECT COUNT(*) FROM reservations) AS reservations,
                       (SELECT COUNT(*) FROM charging_sessions) AS sessions,
                       (SELECT COALESCE(SUM(total_amount),0) FROM invoices) AS invoiced
            """).fetchone()
        return render_template("index.html", stations=stations, summary=summary)
    except Exception as exc:
        return render_template("index.html", stations=[], summary=None, db_error=str(exc))

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
    except Exception as exc:
        flash(f"Reservation failed; check IDs, port status and overlapping times. {exc}", "error")
    return redirect(url_for("main.index"))
