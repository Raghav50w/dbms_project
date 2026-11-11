# ChargePoint — EV Charging Station Reservation and Billing System

Full-stack DBMS course project scaffold for station discovery, port reservation, charging sessions, energy-based invoices, simulated payments, and operator reports.

## Mid-semester deliverables included
- `docs/midsem_design_document.pdf` — design document, five pages maximum.
- `docs/application_design.md` — problem statement, users, assumptions, architecture, workflows, normalization, constraints.
- `docs/ERD.mmd` — Mermaid ERD source.
- `sql/schema.sql` — PostgreSQL schema, constraints, indexes, view and trigger.
- `sql/reporting_queries.sql` — 10 substantial SQL queries.
- `sql/transaction_examples.sql` — reservation, session completion/invoicing and payment transactions.
- Flask scaffold, frontend, synthetic data generator, tests, evaluation checklist.

## Stack
PostgreSQL 15+, Python 3.11+, Flask, psycopg 3, HTML/CSS, pytest.

## Setup
1. Create a PostgreSQL database: `CREATE DATABASE chargepoint;`
2. Create a virtual environment and install: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`, then set `DATABASE_URL`.
4. Apply schema: `psql "$DATABASE_URL" -f sql/schema.sql`
5. Populate synthetic data: `python seed_data.py`
6. Run: `flask --app app.py run --debug`
7. Visit `http://127.0.0.1:5000`.

The seed generator is intended for a fresh schema. The data is synthetic and includes at least 500 rows across entities. 

## Core workflows
1. **Reservation** (`/`): filter stations by city, reserve a port for a time window, cancel a confirmed reservation, delete a cancelled one. PostgreSQL rejects overlapping bookings.
2. **Session and invoice** (`/sessions`): start a session with a start meter reading and tariff; ending it closes the session, records the end reading and creates the invoice in one transaction. An end reading below the start reading is rejected.
3. **Payment** (`/sessions`): record a simulated payment; the trigger updates the invoice to unpaid, partially paid or paid. Payments above the outstanding balance are rejected.
4. **Reporting** (`/reports`): station utilization, monthly revenue, cancellation/no-show rate, session duration (CTE) and outstanding balances.

## Important design decisions
- PostgreSQL `tstzrange` plus a GiST exclusion constraint prevents overlapping active reservations for the same port.
- Meter readings cannot decrease; energy is `end_meter_kwh - start_meter_kwh`.
- Invoices snapshot the applicable energy price and service fee.
- Payments are separate rows so partial payments and failed attempts are representable.
- Payment-state trigger, utilization view, indexes and integrity constraints demonstrate DBMS features.
- This is an academic prototype: no real charger hardware or payment provider is connected.

## Team contributions
| Member | ID | Contribution |
|---|---|---|
| Raghav Mithinti | 2023A3PS0296H | Requirements gathering, ER/EER diagrams and relational database design |
| Aaditya Rajput | 2023A8PS0384H | SQL schema creation, constraints, relationships and seed/sample data |
| Akhil Thindi | 2023AAPS0172H | Flask backend, routes, API handling and application logic |
| Samrat Chaturvedi | 2023A7PS0125H | Frontend development (HTML/CSS/JavaScript), UI design and integration with Flask |
| Kartikeya Srivastava | 2023A3PS0385 | Testing and debugging, test reports, project documentation and final presentation |
