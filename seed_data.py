"""Generate synthetic ChargePoint demo records. Apply sql/schema.sql first."""
import os, random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from dotenv import load_dotenv
import psycopg

load_dotenv()
url=os.environ.get("DATABASE_URL")
if not url: raise SystemExit("Set DATABASE_URL in .env")
random.seed(42)
names=["Aarav Sharma","Diya Reddy","Ishaan Rao","Ananya Iyer","Kabir Mehta","Saanvi Patel","Arjun Nair","Mira Das"]
cities=[("Hyderabad","HITEC City"),("Secunderabad","SP Road"),("Hyderabad","Gachibowli"),("Warangal","Hanamkonda"),("Vijayawada","Benz Circle")]
connectors=["CCS2","Type2","GB/T"]
makes=[("Tata","Nexon EV"),("MG","ZS EV"),("Hyundai","Kona"),("BYD","Atto 3"),("Mahindra","XUV400")]
now=datetime.now(timezone.utc)

with psycopg.connect(url) as c:
    for i in range(1,121):
        c.execute("INSERT INTO drivers(full_name,email,phone) VALUES(%s,%s,%s)",
                  (random.choice(names)+f" {i}",f"driver{i}@example.test",f"+919900{i:06d}"))
    for i in range(1,161):
        make,model=random.choice(makes)
        c.execute("""INSERT INTO vehicles(driver_id,registration_no,make,model,battery_capacity_kwh,connector_type)
                     VALUES(%s,%s,%s,%s,%s,%s)""",
                  (random.randint(1,120),f"TS-EV-{i:05d}",make,model,random.choice([30,40,50,60,70,80]),random.choice(connectors)))
    for i in range(1,13):
        city,area=cities[(i-1)%len(cities)]
        c.execute("INSERT INTO stations(name,address,city,latitude,longitude) VALUES(%s,%s,%s,%s,%s)",
                  (f"ChargePoint {area} {i}",f"{area} Main Road, Plot {i}",city,17.4+i/100,78.3+i/100))
    for sid in range(1,13):
        for p in range(1,5):
            c.execute("""INSERT INTO charging_ports(station_id,port_code,connector_type,max_power_kw)
                         VALUES(%s,%s,%s,%s)""",(sid,f"P{p}",random.choice(connectors),random.choice([7.4,11,22,50,60,120])))
        c.execute("""INSERT INTO tariffs(station_id,tariff_name,price_per_kwh,service_fee,valid_from)
                     VALUES(%s,'Standard',%s,10,%s)""",
                  (sid,random.choice([Decimal("12.50"),Decimal("14.00"),Decimal("15.50"),Decimal("18.00")]),now-timedelta(days=365)))
    # Create 180 reservations over non-overlapping daily windows per port.
    for i in range(180):
        port=random.randint(1,48); day=random.randint(-20,25); slot=random.randint(0,7)
        start=(now+timedelta(days=day)).replace(hour=slot*3,minute=0,second=0,microsecond=0)
        status=random.choice(["confirmed","cancelled","no_show"])
        c.execute("SAVEPOINT reservation_attempt")
        try:
            c.execute("""INSERT INTO reservations(driver_id,vehicle_id,port_id,reserved_period,status)
                         VALUES(%s,%s,%s,tstzrange(%s,%s,'[)'),%s)""",
                      (random.randint(1,120),random.randint(1,160),port,start,start+timedelta(hours=1),status))
            c.execute("RELEASE SAVEPOINT reservation_attempt")
        except psycopg.errors.ExclusionViolation:
            c.execute("ROLLBACK TO SAVEPOINT reservation_attempt")
            c.execute("RELEASE SAVEPOINT reservation_attempt")
    # 70 synthetic completed sessions and invoices.
    for i in range(70):
        driver=random.randint(1,120); vehicle=random.randint(1,160); port=random.randint(1,48)
        tariff=(port-1)//4+1
        started=now-timedelta(days=random.randint(1,90),hours=random.randint(1,10))
        startk=Decimal(random.randint(100,10000))/Decimal(10); energy=Decimal(random.randint(5,70)); endk=startk+energy
        row=c.execute("""INSERT INTO charging_sessions(reservation_id,driver_id,vehicle_id,port_id,tariff_id,
                         started_at,ended_at,start_meter_kwh,end_meter_kwh,status)
                         VALUES(NULL,%s,%s,%s,%s,%s,%s,%s,%s,'completed') RETURNING session_id""",
                      (driver,vehicle,port,tariff,started,started+timedelta(minutes=60),startk,endk)).fetchone()
        c.execute("""INSERT INTO meter_readings(session_id,recorded_at,meter_kwh,reading_type)
                     VALUES(%s,%s,%s,'start'),(%s,%s,%s,'end')""",
                  (row[0],started,startk,row[0],started+timedelta(minutes=60),endk))
        t=c.execute("SELECT price_per_kwh,service_fee FROM tariffs WHERE tariff_id=%s",(tariff,)).fetchone()
        inv=c.execute("""INSERT INTO invoices(session_id,tariff_id,energy_kwh,price_per_kwh,service_fee)
                         VALUES(%s,%s,%s,%s,%s) RETURNING invoice_id,total_amount""",
                      (row[0],tariff,energy,t[0],t[1])).fetchone()
        if i%4:
            amount=inv[1] if i%5 else max(Decimal("1.00"),inv[1]/2)
            c.execute("""INSERT INTO payments(invoice_id,amount,payment_method,payment_reference,status)
                         VALUES(%s,%s,'demo',%s,'successful')""",(inv[0],amount,f"SEED-PAY-{i:04d}"))
    c.commit()
with psycopg.connect(url) as c:
    tables=["drivers","vehicles","stations","charging_ports","tariffs","reservations","charging_sessions","meter_readings","invoices","payments"]
    total=0
    for t in tables:
        n=c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        total+=n
        print(f"{t}: {n}")
    print("Total rows:",total)
