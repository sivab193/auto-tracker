def test_family_create_and_audit(client):
    resp = client.post("/api/families", json={"name": "The Smiths"})
    assert resp.status_code == 201, resp.text
    fam = resp.json()
    assert fam["name"] == "The Smiths"
    assert len(fam["members"]) == 1
    assert fam["members"][0]["role"] == "admin"

    fid = fam["id"]

    # Create an invite.
    resp = client.post(f"/api/families/{fid}/invites", json={"role": "viewer", "max_uses": 3})
    assert resp.status_code == 201, resp.text
    invite = resp.json()
    assert invite["role"] == "viewer"
    assert len(invite["code"]) > 0

    # Audit log records the family + invite creation.
    audit = client.get(f"/api/families/{fid}/audit").json()
    actions = {row["action"] for row in audit}
    assert "family.create" in actions
    assert "invite.create" in actions


def test_share_vehicle_into_family(client):
    fam = client.post("/api/families", json={"name": "Garage"}).json()
    v = client.post(
        "/api/vehicles",
        json={"registration_number": "DL01AA0001", "family_id": fam["id"]},
    )
    assert v.status_code == 201, v.text
    assert v.json()["family_id"] == fam["id"]
