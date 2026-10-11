-- Q1: Station utilization
SELECT * FROM v_station_utilization ORDER BY energy_sold_kwh DESC;

-- Q2: Monthly collected revenue by station
SELECT date_trunc('month',p.paid_at) AS month,s.name,SUM(p.amount) AS revenue_inr
FROM payments p JOIN invoices i USING(invoice_id) JOIN charging_sessions cs USING(session_id)
JOIN charging_ports cp USING(port_id) JOIN stations s USING(station_id)
WHERE p.status='successful' GROUP BY 1,2 ORDER BY 1 DESC,3 DESC;

-- Q3: Port usage and energy
SELECT s.name,cp.port_code,COUNT(cs.session_id) AS sessions,COALESCE(SUM(i.energy_kwh),0) AS energy_kwh
FROM charging_ports cp JOIN stations s USING(station_id)
LEFT JOIN charging_sessions cs ON cs.port_id=cp.port_id AND cs.status='completed'
LEFT JOIN invoices i USING(session_id) GROUP BY s.name,cp.port_code ORDER BY sessions DESC,energy_kwh DESC;

-- Q4: Driver lifetime spend
SELECT d.driver_id,d.full_name,COUNT(DISTINCT cs.session_id) AS sessions,
 COALESCE(SUM(p.amount) FILTER(WHERE p.status='successful'),0) AS paid_inr
FROM drivers d LEFT JOIN charging_sessions cs USING(driver_id)
LEFT JOIN invoices i USING(session_id) LEFT JOIN payments p USING(invoice_id)
GROUP BY d.driver_id,d.full_name ORDER BY paid_inr DESC;

-- Q5: Cancellation/no-show rate by station
SELECT s.station_id,s.name,COUNT(r.reservation_id) AS total,
 COUNT(r.reservation_id) FILTER(WHERE r.status IN('cancelled','no_show')) AS problem_reservations,
 ROUND(100.0*COUNT(r.reservation_id) FILTER(WHERE r.status IN('cancelled','no_show'))/NULLIF(COUNT(r.reservation_id),0),2) AS rate_pct
FROM stations s JOIN charging_ports cp USING(station_id) LEFT JOIN reservations r USING(port_id)
GROUP BY s.station_id,s.name ORDER BY rate_pct DESC NULLS LAST;

-- Q6: CTE for session duration and energy
WITH metrics AS (SELECT session_id,port_id,end_meter_kwh-start_meter_kwh AS energy,
 EXTRACT(EPOCH FROM ended_at-started_at)/60 AS minutes FROM charging_sessions WHERE status='completed')
SELECT s.name,cp.port_code,COUNT(*) AS sessions,ROUND(AVG(minutes)::numeric,2) AS avg_minutes,
 ROUND(AVG(energy)::numeric,2) AS avg_kwh FROM metrics m JOIN charging_ports cp USING(port_id)
JOIN stations s USING(station_id) GROUP BY s.name,cp.port_code ORDER BY sessions DESC;

-- Q7: Outstanding invoice balances
SELECT i.invoice_id,d.full_name,i.total_amount,
 COALESCE(SUM(p.amount) FILTER(WHERE p.status='successful'),0) AS paid,
 i.total_amount-COALESCE(SUM(p.amount) FILTER(WHERE p.status='successful'),0) AS outstanding
FROM invoices i JOIN charging_sessions cs USING(session_id) JOIN drivers d USING(driver_id)
LEFT JOIN payments p USING(invoice_id) WHERE i.status IN('unpaid','partially_paid')
GROUP BY i.invoice_id,d.full_name,i.total_amount ORDER BY outstanding DESC;

-- Q8: Vehicles with no available compatible port at each active station
SELECT v.vehicle_id,v.registration_no,s.station_id,s.name
FROM vehicles v CROSS JOIN stations s WHERE s.is_active AND NOT EXISTS
 (SELECT 1 FROM charging_ports cp WHERE cp.station_id=s.station_id AND cp.connector_type=v.connector_type AND cp.status='available');

-- Q9: Confirmed reservations in the next 24 hours
SELECT r.reservation_id,d.full_name,s.name,cp.port_code,lower(r.reserved_period) AS starts_at,upper(r.reserved_period) AS ends_at
FROM reservations r JOIN drivers d USING(driver_id) JOIN charging_ports cp USING(port_id) JOIN stations s USING(station_id)
WHERE r.status='confirmed' AND lower(r.reserved_period)>=now() AND lower(r.reserved_period)<now()+interval '24 hours'
ORDER BY lower(r.reserved_period);

-- Q10: Invoice/energy totals by tariff
SELECT s.name,t.tariff_name,t.price_per_kwh,COUNT(i.invoice_id) AS invoices,
 COALESCE(SUM(i.energy_kwh),0) AS energy_kwh,COALESCE(SUM(i.total_amount),0) AS invoiced_inr
FROM tariffs t JOIN stations s USING(station_id) LEFT JOIN invoices i USING(tariff_id)
GROUP BY s.name,t.tariff_name,t.price_per_kwh ORDER BY invoiced_inr DESC;
