def test_listar_materias_vazio(client):
    response = client.get("/api/materias/")
    assert response.status_code == 200
    assert response.json() == []


def test_criar_materia(client):
    payload = {"name": "Cálculo I", "teacher": "Prof. Silva", "semester": 1, "year": 2024, "num_exams": 3}
    response = client.post("/api/materias/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cálculo I"
    assert data["id"] is not None
    assert data["num_exams"] == 3
    assert len(data["nps"]) == 3


def test_criar_materia_gera_nps(client):
    materia = client.post("/api/materias/", json={"name": "Física", "num_exams": 2}).json()
    assert len(materia["nps"]) == 2
    assert materia["nps"][0]["np_number"] == 1
    assert materia["nps"][1]["np_number"] == 2


def test_detalhar_materia(client):
    criada = client.post("/api/materias/", json={"name": "Física"}).json()
    response = client.get(f"/api/materias/{criada['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Física"


def test_detalhar_materia_nao_encontrada(client):
    response = client.get("/api/materias/9999")
    assert response.status_code == 404


def test_atualizar_materia(client):
    criada = client.post("/api/materias/", json={"name": "Programação", "num_exams": 2}).json()
    response = client.put(f"/api/materias/{criada['id']}", json={"name": "Programação II", "num_exams": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Programação II"
    assert len(data["nps"]) == 3


def test_remover_materia(client):
    criada = client.post("/api/materias/", json={"name": "Química"}).json()
    response = client.delete(f"/api/materias/{criada['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/materias/{criada['id']}").status_code == 404


def test_situacao_materia_aprovado(client):
    materia = client.post("/api/materias/", json={"name": "Álgebra", "num_exams": 1}).json()
    client.post("/api/notas/", json={
        "value": 85.0, "grade_type": "NP1",
        "date": "2024-04-10", "subject_id": materia["id"]
    })
    response = client.get(f"/api/materias/{materia['id']}/situacao")
    assert response.status_code == 200
    data = response.json()
    assert data["average"] == 85.0
    assert data["status"] == "aprovado"
