def _criar_materia(client, nome="Matéria Teste", num_exams=2):
    return client.post("/api/materias/", json={"name": nome, "num_exams": num_exams}).json()


def test_inserir_nota(client):
    materia = _criar_materia(client)
    payload = {"value": 75.0, "grade_type": "NP1", "date": "2024-05-15", "subject_id": materia["id"]}
    response = client.post("/api/notas/", json=payload)
    assert response.status_code == 201
    assert response.json()["value"] == 75.0


def test_nota_duplicada_rejeitada(client):
    materia = _criar_materia(client)
    payload = {"value": 70.0, "grade_type": "NP1", "date": "2024-05-15", "subject_id": materia["id"]}
    client.post("/api/notas/", json=payload)
    response = client.post("/api/notas/", json=payload)
    assert response.status_code == 409


def test_listar_notas_por_materia(client):
    s1 = _criar_materia(client, "Física")
    s2 = _criar_materia(client, "Química")
    client.post("/api/notas/", json={"value": 90.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": s1["id"]})
    client.post("/api/notas/", json={"value": 60.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": s2["id"]})
    response = client.get(f"/api/notas/?subject_id={s1['id']}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["value"] == 90.0


def test_atualizar_nota(client):
    materia = _criar_materia(client)
    nota = client.post("/api/notas/", json={"value": 50.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]}).json()
    response = client.put(f"/api/notas/{nota['id']}", json={"value": 80.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    assert response.status_code == 200
    assert response.json()["value"] == 80.0


def test_remover_nota(client):
    materia = _criar_materia(client)
    nota = client.post("/api/notas/", json={"value": 70.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]}).json()
    response = client.delete(f"/api/notas/{nota['id']}")
    assert response.status_code == 204


def test_nota_valor_invalido_acima_100(client):
    materia = _criar_materia(client)
    response = client.post("/api/notas/", json={"value": 101.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    assert response.status_code == 422


def test_media_incompleta_nao_calculada(client):
    materia = _criar_materia(client, num_exams=2)
    client.post("/api/notas/", json={"value": 80.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    response = client.get("/api/notas/medias")
    assert response.status_code == 200
    dado = next(r for r in response.json() if r["subject_id"] == materia["id"])
    assert dado["average"] is None
    assert dado["nps_lancadas"] == 1
    assert dado["nps_total"] == 2
    assert dado["min_necessaria"] is not None


def test_media_completa_calculada(client):
    materia = _criar_materia(client, num_exams=2)
    client.post("/api/notas/", json={"value": 70.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    client.post("/api/notas/", json={"value": 90.0, "grade_type": "NP2", "date": "2024-06-01", "subject_id": materia["id"]})
    response = client.get("/api/notas/medias")
    dado = next(r for r in response.json() if r["subject_id"] == materia["id"])
    assert dado["average"] == 80.0
    assert dado["status"] == "aprovado"


def test_status_final(client):
    materia = _criar_materia(client, num_exams=1)
    client.post("/api/notas/", json={"value": 50.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    response = client.get("/api/notas/medias")
    dado = next(r for r in response.json() if r["subject_id"] == materia["id"])
    assert dado["status"] == "final"
    # final_needed = 100 - media = 100 - 50 = 50
    assert dado["final_needed"] == 50.0


def test_aprovado_via_exame_final(client):
    materia = _criar_materia(client, num_exams=1)
    client.post("/api/notas/", json={"value": 50.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    client.post("/api/notas/", json={"value": 60.0, "grade_type": "Exame Final", "date": "2024-07-01", "subject_id": materia["id"]})
    response = client.get("/api/notas/medias")
    dado = next(r for r in response.json() if r["subject_id"] == materia["id"])
    assert dado["status"] == "aprovado_final"
    assert dado["media_final"] == 55.0


def test_reprovado_via_exame_final(client):
    materia = _criar_materia(client, num_exams=1)
    client.post("/api/notas/", json={"value": 50.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    client.post("/api/notas/", json={"value": 40.0, "grade_type": "Exame Final", "date": "2024-07-01", "subject_id": materia["id"]})
    response = client.get("/api/notas/medias")
    dado = next(r for r in response.json() if r["subject_id"] == materia["id"])
    assert dado["status"] == "reprovado_final"
    assert dado["media_final"] == 45.0


def test_status_reprovado(client):
    materia = _criar_materia(client, num_exams=1)
    client.post("/api/notas/", json={"value": 20.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    response = client.get("/api/notas/medias")
    dado = next(r for r in response.json() if r["subject_id"] == materia["id"])
    assert dado["status"] == "reprovado"


def test_min_necessaria_calculo(client):
    materia = _criar_materia(client, num_exams=2)
    client.post("/api/notas/", json={"value": 40.0, "grade_type": "NP1", "date": "2024-05-01", "subject_id": materia["id"]})
    response = client.get("/api/notas/medias")
    dado = next(r for r in response.json() if r["subject_id"] == materia["id"])
    # pesos iguais (1,1): (40*1 + X*1)/2 >= 60 → X >= 80
    assert dado["min_necessaria"] == 80.0
    assert dado["impossivel_aprovar"] is False
