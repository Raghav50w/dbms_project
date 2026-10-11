from decimal import Decimal

def total(energy_kwh, price_per_kwh, service_fee):
    energy = (Decimal(str(energy_kwh))*Decimal(str(price_per_kwh))).quantize(Decimal("0.01"))
    return energy + Decimal(str(service_fee))

def test_billing_formula():
    assert total("12.5","14.00","10.00") == Decimal("185.00")

def test_service_fee_with_zero_energy():
    assert total("0","14.00","10.00") == Decimal("10.00")
