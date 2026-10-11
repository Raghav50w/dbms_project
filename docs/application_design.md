# Application Design — ChargePoint

## Problem statement
Drivers need to locate a compatible charging port, reserve a time slot, charge a vehicle and receive an accurate energy-based invoice. Operators need to manage availability, tariffs, sessions, outages and revenue. The relational database is the source of truth for reservations, sessions, readings, invoices and payments.

## Users
- **Driver:** registers vehicles, reserves ports, views sessions/invoices and records demo payments.
- **Operator:** manages port status/tariffs, starts and ends sessions, reviews reports.
- **Administrator:** maintains reference data and system-wide metrics.

## Assumptions and business rules
- Academic prototype; no real payment gateway or charger hardware.
- Energy = end cumulative meter reading − start cumulative meter reading.
- Invoice = energy kWh × price per kWh + service fee.
- Invoice stores tariff price and service-fee snapshots so later tariff changes do not rewrite historic bills.
- Timestamps are `TIMESTAMPTZ`; UI must normalize station-local time.
- Reservation ranges are half-open `[start,end)`: a slot ending at 11:00 may be followed by one starting at 11:00.
- PostgreSQL exclusion constraint rejects overlapping active reservations for one port.
- Only successful payment rows count toward invoice settlement; payment integration is simulated.

## Architecture
```text
Browser UI (HTML/CSS)
   -> Flask route handlers
      -> psycopg parameterized SQL
         -> PostgreSQL
            - PK/FK/UNIQUE/CHECK constraints
            - range exclusion constraint
            - transactions and indexes
            - payment status trigger
            - station utilization view
```

## Workflows
### A. Reserve a port
1. Driver chooses station, compatible port and time range.
2. Backend validates form and driver/vehicle/port records.
3. Insert reservation in a transaction.
4. Exclusion constraint rejects overlapping active reservations.
5. UI shows confirmation or conflict.

### B. Start/end a session and bill
1. Operator starts a session with a start meter reading and applicable tariff.
2. At completion, operator records end time and final meter reading.
3. Validate end reading >= start reading.
4. One transaction closes the session and creates its invoice.
5. Invoice snapshots price and service fee.

### C. Record payment
1. Driver selects invoice and enters a simulated payment.
2. Payment row is inserted with method/reference/status.
3. Trigger recalculates invoice state: unpaid, partially paid or paid.
4. UI displays invoice state and balance.

### D. Reports
Operator views port utilization, energy sold, revenue, outstanding invoices, cancellation/no-show rate and connector compatibility using joins, aggregates, CTEs and a view.

## Relational entities
`drivers`, `vehicles`, `stations`, `charging_ports`, `tariffs`, `reservations`, `charging_sessions`, `meter_readings`, `invoices`, `payments`.

## Integrity rules
Unique driver email, vehicle registration, station/port code and payment reference. Positive battery capacity and port power. Nonnegative prices, meter readings and energy. Reservation ranges must be non-empty; active port reservations cannot overlap. One invoice per session. Payments reference invoices and only successful payments count toward settlement.

## Normalization
- **1NF:** atomic attributes; readings, payments, ports and vehicles are separate rows.
- **2NF:** single-column primary keys; each non-key attribute depends on the row's key.
- **3NF:** driver, station, port, tariff, session, invoice and payment facts are stored in their own relations. Names/address/contact fields are not duplicated in reservation rows.
- Invoice price/service fee are intentionally snapshotted to preserve historical billing if tariffs change.

## SQL and DBMS features
10 reporting queries cover joins, filtered aggregates, CTEs, `NOT EXISTS`, revenue, utilization, energy, and outstanding balances. Features include transactions, exclusion constraint, primary/foreign/unique/check constraints, trigger, view and indexes.

## Stack and scope
PostgreSQL 15+, Python 3.11+, Flask, psycopg 3, HTML/CSS and pytest. Session/payment/report screens are a planned extension; SQL examples and the schema provide their DBMS implementation patterns.
