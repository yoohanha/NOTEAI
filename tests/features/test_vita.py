"""NOTE_PAPER 이력 API 테스트"""


def test_vita_requires_auth(client):
    assert client.get("/api/vita").status_code in (401, 403)


def test_publication_create_and_delete(client, auth_headers):
    created = client.post(
        "/api/vita/publications",
        json={
            "title": "Graph Notes",
            "venue": "ACL",
            "year": "2025",
            "role": "제1저자",
            "link_or_status": "https://example.com/p",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    item = created.json()["data"]
    assert item["title"] == "Graph Notes"

    listed = client.get("/api/vita", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["data"]["publications"]) == 1

    deleted = client.delete(f"/api/vita/publications/{item['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert client.get("/api/vita", headers=auth_headers).json()["data"]["publications"] == []


def test_rejects_empty_publication_title(client, auth_headers):
    response = client.post(
        "/api/vita/publications",
        json={"title": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_certificate_and_teaching_flow(client, auth_headers):
    cert = client.post(
        "/api/vita/certificates",
        json={"name": "정보처리기사", "organization": "HRDK", "acquired_on": "2024-05-01"},
        headers=auth_headers,
    )
    assert cert.status_code == 201

    teach = client.post(
        "/api/vita/teachings",
        json={
            "institution": "NoteAI Univ",
            "course": "딥러닝 입문",
            "period": "2024-2025",
            "role": "강사",
        },
        headers=auth_headers,
    )
    assert teach.status_code == 201

    listed = client.get("/api/vita", headers=auth_headers).json()["data"]
    assert listed["certificates"][0]["name"] == "정보처리기사"
    assert listed["teachings"][0]["institution"] == "NoteAI Univ"

    assert client.delete(
        f"/api/vita/certificates/{cert.json()['data']['id']}",
        headers=auth_headers,
    ).status_code == 200
    assert client.delete(
        f"/api/vita/teachings/{teach.json()['data']['id']}",
        headers=auth_headers,
    ).status_code == 200
