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

The seed generator is intended for a fresh schema. The data is synthetic and includes at least 500 rows across entities. The app currently implements station overview and reservation creation; session, invoice, payment and report workflows are documented and provided as SQL patterns for the team to complete.

## Core workflows
1. Reserve a port for a time window.
2. Start/end a session and generate an invoice from meter readings.
3. Record a simulated payment and update invoice settlement status.
4. Review station utilization, energy, revenue and outstanding invoices.

## Important design decisions
- PostgreSQL `tstzrange` plus a GiST exclusion constraint prevents overlapping active reservations for the same port.
- Meter readings cannot decrease; energy is `end_meter_kwh - start_meter_kwh`.
- Invoices snapshot the applicable energy price and service fee.
- Payments are separate rows so partial payments and failed attempts are representable.
- Payment-state trigger, utilization view, indexes and integrity constraints demonstrate DBMS features.
- This is an academic prototype: no real charger hardware or payment provider is connected.

- ## Team contributions
| Member | Contribution |
|---|---|---|
| Raghav Mithinti | Requirements gathering, ER/EER diagrams and relational database design |
| Aaditya Rajput | SQL schema creation, constraints, relationships and seed/sample data |
| Akhil Thindi | Flask backend, routes, API handling and application logic |
| Samrat Chaturvedi | Frontend development (HTML/CSS/JavaScript), UI design and integration with Flask |
| Kartikeya Srivastava | Testing and debugging, test reports, project documentation and final presentation |
