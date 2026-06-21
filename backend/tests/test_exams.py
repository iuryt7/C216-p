def _criar_materia(client, nome="Matéria"):
    return client.post("/api/materias/", json={"name": nome}).json()


def test_criar_evento_com_materias(client):
    s1 = _criar_materia(client, "Cálculo")
    s2 = _criar_materia(client, "Álgebra")
    payload = {
        "title": "Prova Integrada",
        "exam_date": "2024-06-20",
        "tipo_evento": "prova",
        "subject_ids": [s1["id"], s2["id"]]
    }
    response = client.post("/api/eventos/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Prova Integrada"
    assert data["tipo_evento"] == "prova"
    assert len(data["subjects"]) == 2


def test_criar_evento_reposicao(client):
    payload = {"title": "Reposição", "exam_date": "2024-06-20", "tipo_evento": "reposicao", "subject_ids": []}
    response = client.post("/api/eventos/", json=payload)
    assert response.status_code == 201
    assert response.json()["tipo_evento"] == "reposicao"


def test_tipo_evento_invalido(client):
    payload = {"title": "Evento X", "exam_date": "2024-06-20", "tipo_evento": "invalido", "subject_ids": []}
    response = client.post("/api/eventos/", json=payload)
    assert response.status_code == 422


def test_listar_eventos(client):
    s = _criar_materia(client)
    client.post("/api/eventos/", json={"title": "P1", "exam_date": "2024-06-01", "tipo_evento": "prova", "subject_ids": [s["id"]]})
    client.post("/api/eventos/", json={"title": "P2", "exam_date": "2024-07-01", "tipo_evento": "prova", "subject_ids": [s["id"]]})
    response = client.get("/api/eventos/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_atualizar_evento(client):
    s = _criar_materia(client)
    evento = client.post("/api/eventos/", json={"title": "Antigo", "exam_date": "2024-06-01", "tipo_evento": "prova", "subject_ids": [s["id"]]}).json()
    response = client.put(f"/api/eventos/{evento['id']}", json={"title": "Novo", "exam_date": "2024-06-05", "tipo_evento": "reposicao", "subject_ids": [s["id"]]})
    assert response.status_code == 200
    assert response.json()["title"] == "Novo"
    assert response.json()["tipo_evento"] == "reposicao"


def test_remover_evento(client):
    s = _criar_materia(client)
    evento = client.post("/api/eventos/", json={"title": "Deletar", "exam_date": "2024-06-01", "tipo_evento": "outro", "subject_ids": [s["id"]]}).json()
    response = client.delete(f"/api/eventos/{evento['id']}")
    assert response.status_code == 204


def test_filtro_por_data(client):
    s = _criar_materia(client)
    client.post("/api/eventos/", json={"title": "Passada", "exam_date": "2024-01-01", "tipo_evento": "prova", "subject_ids": [s["id"]]})
    client.post("/api/eventos/", json={"title": "Futura", "exam_date": "2025-01-01", "tipo_evento": "prova", "subject_ids": [s["id"]]})
    response = client.get("/api/eventos/?from_date=2024-06-01")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Futura"
