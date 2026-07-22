from datetime import date, timedelta


def test_fuel_mileage_calculation(client, vehicle):
    vid = vehicle["id"]
    # Three consecutive full-tank fills.
    fills = [
        {"fill_date": "2026-01-01", "odometer": 10000, "quantity": 40, "total_cost": 4000, "is_full_tank": True},
        {"fill_date": "2026-01-10", "odometer": 10400, "quantity": 40, "total_cost": 4000, "is_full_tank": True},
        {"fill_date": "2026-01-20", "odometer": 10900, "quantity": 50, "total_cost": 5000, "is_full_tank": True},
    ]
    for f in fills:
        assert client.post(f"/api/vehicles/{vid}/fuel", json=f).status_code == 201

    logs = client.get(f"/api/vehicles/{vid}/fuel").json()
    by_odo = {l["odometer"]: l for l in logs}

    # First fill: no prior full tank → no efficiency.
    assert by_odo[10000]["efficiency"] is None
    # Second: 400 km on 40 units → 10.0 distance/unit.
    assert by_odo[10400]["efficiency"] == 10.0
    assert by_odo[10400]["distance"] == 400
    # Third: 500 km on 50 units → 10.0.
    assert by_odo[10900]["efficiency"] == 10.0


def test_expiry_alert_sweep(client, vehicle):
    vid = vehicle["id"]
    soon = (date.today() + timedelta(days=5)).isoformat()
    files = {"file": ("puc.txt", b"puc", "text/plain")}
    client.post(
        f"/api/vehicles/{vid}/documents",
        files=files,
        data={"doc_type": "pollution", "auto_ocr": "false", "expiry_date": soon},
    )

    swept = client.post("/api/alerts/sweep").json()
    assert swept["created"] >= 1

    alerts = client.get("/api/alerts").json()
    assert any("expiring" in a["title"].lower() for a in alerts)

    # Sweeping again should not duplicate the alert.
    before = len(client.get("/api/alerts").json())
    client.post("/api/alerts/sweep")
    after = len(client.get("/api/alerts").json())
    assert before == after


def test_alert_acknowledge(client, vehicle):
    soon = (date.today() + timedelta(days=3)).isoformat()
    files = {"file": ("ins.txt", b"ins", "text/plain")}
    client.post(
        f"/api/vehicles/{vehicle['id']}/documents",
        files=files,
        data={"doc_type": "insurance", "auto_ocr": "false", "expiry_date": soon},
    )
    client.post("/api/alerts/sweep")
    alert = client.get("/api/alerts").json()[0]
    resp = client.post(f"/api/alerts/{alert['id']}/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"
