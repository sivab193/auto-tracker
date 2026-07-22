def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["single_user"] is True


def test_vehicle_crud(client):
    # Create
    resp = client.post(
        "/api/vehicles",
        json={"registration_number": "MH12XY9999", "nickname": "Daily", "odometer": 15000},
    )
    assert resp.status_code == 201, resp.text
    vid = resp.json()["id"]
    assert resp.json()["display_name"] == "Daily"

    # List
    resp = client.get("/api/vehicles")
    assert resp.status_code == 200
    assert any(v["id"] == vid for v in resp.json())

    # Update
    resp = client.patch(f"/api/vehicles/{vid}", json={"color": "Blue", "odometer": 16000})
    assert resp.status_code == 200
    assert resp.json()["color"] == "Blue"

    # Get detail
    resp = client.get(f"/api/vehicles/{vid}")
    assert resp.status_code == 200
    assert resp.json()["documents"] == []

    # Delete
    resp = client.delete(f"/api/vehicles/{vid}")
    assert resp.status_code == 204
    assert client.get(f"/api/vehicles/{vid}").status_code == 404


def test_document_upload_without_ocr(client, vehicle):
    files = {"file": ("policy.txt", b"dummy insurance policy", "text/plain")}
    data = {"doc_type": "insurance", "title": "My Policy", "auto_ocr": "false",
            "expiry_date": "2027-01-15"}
    resp = client.post(f"/api/vehicles/{vehicle['id']}/documents", files=files, data=data)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["doc_type"] == "insurance"
    assert body["expiry_date"] == "2027-01-15"
    assert body["version"] == 1

    # Download round-trips the bytes.
    resp = client.get(f"/api/documents/{body['id']}/download")
    assert resp.status_code == 200
    assert resp.content == b"dummy insurance policy"


def test_document_versioning(client, vehicle):
    files = {"file": ("v1.txt", b"first", "text/plain")}
    r1 = client.post(
        f"/api/vehicles/{vehicle['id']}/documents",
        files=files, data={"doc_type": "pollution", "auto_ocr": "false"},
    )
    doc1 = r1.json()

    files = {"file": ("v2.txt", b"second", "text/plain")}
    r2 = client.post(
        f"/api/vehicles/{vehicle['id']}/documents",
        files=files, data={"auto_ocr": "false", "supersede_id": str(doc1["id"])},
    )
    doc2 = r2.json()
    assert doc2["version"] == 2
    assert doc2["supersedes_id"] == doc1["id"]

    # Only the current version shows by default.
    current = client.get(f"/api/vehicles/{vehicle['id']}/documents").json()
    ids = {d["id"] for d in current}
    assert doc2["id"] in ids and doc1["id"] not in ids

    # Version history contains both.
    versions = client.get(f"/api/documents/{doc2['id']}/versions").json()
    assert {v["id"] for v in versions} == {doc1["id"], doc2["id"]}
