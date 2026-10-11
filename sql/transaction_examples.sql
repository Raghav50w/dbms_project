-- A. Reserve a port. Overlap is rejected by the exclusion constraint.
BEGIN;
INSERT INTO reservations(driver_id,vehicle_id,port_id,reserved_period,status)
VALUES(1,1,1,tstzrange('2026-11-02 10:00:00+05:30','2026-11-02 11:00:00+05:30','[)'),'confirmed');
COMMIT;

-- B. Finish a session and create its invoice in one transaction. Replace demo IDs/readings.
BEGIN;
WITH done AS (
 UPDATE charging_sessions SET ended_at='2026-11-02 11:00:00+05:30',end_meter_kwh=42.500,status='completed'
 WHERE session_id=1 AND status='in_progress' AND 42.500>=start_meter_kwh
 RETURNING session_id,tariff_id,end_meter_kwh-start_meter_kwh AS energy_kwh
)
INSERT INTO invoices(session_id,tariff_id,energy_kwh,price_per_kwh,service_fee)
SELECT d.session_id,d.tariff_id,d.energy_kwh,t.price_per_kwh,t.service_fee
FROM done d JOIN tariffs t USING(tariff_id);
COMMIT;

-- C. Record a simulated successful payment; trigger updates invoice state.
BEGIN;
INSERT INTO payments(invoice_id,amount,payment_method,payment_reference,status)
VALUES(1,100.00,'demo','DEMO-UNIQUE-0001','successful');
COMMIT;

-- Production hardening: validate driver owns vehicle; port is available; tariff validity;
-- session belongs to reservation; port isn't out of service; and no payment exceeds balance.
