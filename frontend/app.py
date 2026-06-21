import os
from datetime import date, datetime
import calendar
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "semester-manager-secret"

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# 0=Domingo, 1=Segunda, ..., 6=Sábado
DAYS_PT = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]


def api_get(path, params=None):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def api_post(path, data):
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=data, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.HTTPError as e:
        try:
            detalhe = e.response.json().get("detail", str(e))
        except Exception:
            detalhe = str(e)
        return None, detalhe
    except Exception as e:
        return None, str(e)


def api_put(path, data):
    try:
        r = requests.put(f"{BACKEND_URL}{path}", json=data, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.HTTPError as e:
        try:
            detalhe = e.response.json().get("detail", str(e))
        except Exception:
            detalhe = str(e)
        return None, detalhe
    except Exception as e:
        return None, str(e)


def _semestres_disponiveis():
    historico = api_get("/api/materias/historico")
    semestres = [{"key": "ativo", "label": "Semestre Atual"}]
    for g in historico:
        ano = g.get("ano") or 0
        sem = g.get("semestre") or 0
        if sem and ano:
            label = f"{sem}º Semestre de {ano}"
        elif ano:
            label = str(ano)
        else:
            label = "Semestre sem data"
        semestres.append({"key": f"{ano}-{sem}", "label": label})
    return semestres


def _params_api_semestre(key):
    if not key or key == "ativo":
        return {"arquivado": "false"}
    partes = key.split("-")
    if len(partes) == 2:
        return {"arquivado": "true", "ano": partes[0], "semestre": partes[1]}
    return {"arquivado": "false"}


def api_delete(path):
    try:
        requests.delete(f"{BACKEND_URL}{path}", timeout=5)
        return True
    except Exception:
        return False


@app.route("/")
def home():
    semestre_key = request.args.get("semestre_key")
    if semestre_key is not None:
        session["semestre_key"] = semestre_key
    else:
        semestre_key = session.get("semestre_key", "ativo")

    params_sem = _params_api_semestre(semestre_key)
    semestres = _semestres_disponiveis()
    semestre_label = next((s["label"] for s in semestres if s["key"] == semestre_key), "Semestre Atual")
    is_historico = semestre_key != "ativo"

    hoje = date.today()
    medias = api_get("/api/notas/medias", params=params_sem)

    if is_historico:
        proximos = []
        aulas_hoje = []
    else:
        eventos = api_get("/api/eventos/", params={"from_date": hoje.isoformat()})
        proximos = eventos[:5]
        horarios = api_get("/api/horarios/")
        dia_hoje = (hoje.weekday() + 1) % 7
        aulas_hoje = [h for h in horarios if h["day_of_week"] == dia_hoje]

    stats = {
        "aprovadas": sum(1 for m in medias if m.get("status") in ("aprovado", "aprovado_final")),
        "em_risco": sum(1 for m in medias if m.get("status") == "final"),
        "reprovadas": sum(1 for m in medias if m.get("status") in ("reprovado", "reprovado_final")),
        "pendentes": sum(1 for m in medias if m.get("status") is None),
    }
    historico = api_get("/api/materias/historico")
    return render_template("home.html", upcoming=proximos, averages=medias,
                           today_classes=aulas_hoje, today=hoje, days=DAYS_PT,
                           stats=stats, historico=historico,
                           semestres=semestres, semestre_key=semestre_key,
                           semestre_label=semestre_label, is_historico=is_historico)


@app.route("/subjects", methods=["GET", "POST"])
def subjects():
    if request.method == "POST":
        acao = request.form.get("action")
        if acao == "create":
            dados = {
                "name": request.form["name"],
                "teacher": request.form.get("teacher", ""),
                "color_hex": request.form.get("color_hex", "#4f46e5"),
                "semester": int(request.form["semester"]) if request.form.get("semester") else None,
                "year": int(request.form["year"]) if request.form.get("year") else None,
                "num_exams": int(request.form.get("num_exams", 2)),
            }
            _, err = api_post("/api/materias/", dados)
            flash("Matéria criada!" if not err else f"Erro: {err}", "success" if not err else "danger")
        elif acao == "delete":
            api_delete(f"/api/materias/{request.form['subject_id']}")
            flash("Matéria removida!", "success")
        elif acao == "update":
            sid = request.form["subject_id"]
            dados = {
                "name": request.form["name"],
                "teacher": request.form.get("teacher", ""),
                "color_hex": request.form.get("color_hex", "#4f46e5"),
                "semester": int(request.form["semester"]) if request.form.get("semester") else None,
                "year": int(request.form["year"]) if request.form.get("year") else None,
                "num_exams": int(request.form.get("num_exams", 2)),
            }
            _, err = api_put(f"/api/materias/{sid}", dados)
            flash("Matéria atualizada!" if not err else f"Erro: {err}", "success" if not err else "danger")
        elif acao == "arquivar_semestre":
            resultado, err = api_post("/api/materias/arquivar-semestre", {})
            if err:
                flash(f"Erro ao arquivar: {err}", "danger")
            else:
                n = resultado.get("arquivadas", 0) if isinstance(resultado, dict) else 0
                flash(f"Semestre arquivado! {n} matéria(s) arquivada(s).", "success")
        return redirect(url_for("subjects"))

    todas_materias = api_get("/api/materias/", params={"arquivado": "false"})
    arquivadas = api_get("/api/materias/", params={"arquivado": "true"})
    # Agrupar arquivadas por (year, semester)
    historico_local: dict = {}
    for m in arquivadas:
        chave = (m.get("year") or 0, m.get("semester") or 0)
        historico_local.setdefault(chave, []).append(m)
    semestres_arquivados = [
        {"ano": ano, "semestre": sem, "materias": mats}
        for (ano, sem), mats in sorted(historico_local.items(), reverse=True)
    ]
    return render_template("subjects.html", subjects=todas_materias,
                           semestres_arquivados=semestres_arquivados)


@app.route("/grades", methods=["GET", "POST"])
def grades():
    if request.method == "POST":
        acao = request.form.get("action")
        if acao == "create":
            dados = {
                "value": float(request.form["value"]),
                "grade_type": request.form["grade_type"],
                "date": request.form["date"],
                "description": request.form.get("description", ""),
                "subject_id": int(request.form["subject_id"]),
            }
            _, err = api_post("/api/notas/", dados)
            flash("Nota adicionada!" if not err else f"Erro: {err}", "success" if not err else "danger")
        elif acao == "update":
            nota_id = request.form["nota_id"]
            dados = {
                "value": float(request.form["value"]),
                "grade_type": request.form["grade_type"],
                "date": request.form["date"],
                "description": request.form.get("description", ""),
                "subject_id": int(request.form["subject_id"]),
            }
            _, err = api_put(f"/api/notas/{nota_id}", dados)
            flash("Nota atualizada!" if not err else f"Erro: {err}", "success" if not err else "danger")
        elif acao == "delete":
            api_delete(f"/api/notas/{request.form['grade_id']}")
            flash("Nota removida!", "success")
        return redirect(url_for("grades"))

    todas_materias = api_get("/api/materias/")
    subject_id = request.args.get("subject_id")
    params = {"subject_id": subject_id} if subject_id else None
    todas_notas = api_get("/api/notas/", params=params)
    medias = api_get("/api/notas/medias")

    # Monta dicionário {materia_id: set(grade_types já lançados)} para o JS
    notas_por_materia: dict = {}
    for nota in api_get("/api/notas/"):
        sid = nota["subject_id"]
        notas_por_materia.setdefault(sid, [])
        notas_por_materia[sid].append(nota["grade_type"])

    return render_template("grades.html", subjects=todas_materias, grades=todas_notas,
                           averages=medias, selected_subject=subject_id,
                           notas_por_materia=notas_por_materia)


@app.route("/calendar", methods=["GET", "POST"])
def calendar_view():
    if request.method == "POST":
        acao = request.form.get("action")
        if acao == "create":
            subject_id = request.form.get("subject_id", "")
            dados = {
                "title": request.form.get("title", ""),
                "exam_date": request.form["exam_date"],
                "description": request.form.get("description", ""),
                "tipo_evento": request.form.get("tipo_evento", "prova"),
                "subject_ids": [int(subject_id)] if subject_id else [],
            }
            _, err = api_post("/api/eventos/", dados)
            flash("Evento criado!" if not err else f"Erro: {err}", "success" if not err else "danger")
        elif acao == "delete":
            api_delete(f"/api/eventos/{request.form['evento_id']}")
            flash("Evento removido!", "success")
        return redirect(url_for("calendar_view",
                                year=request.form.get("year"), month=request.form.get("month")))

    hoje = date.today()
    ano = int(request.args.get("year", hoje.year))
    mes = int(request.args.get("month", hoje.month))

    cal = calendar.monthcalendar(ano, mes)
    eventos = api_get("/api/eventos/")
    todas_materias = api_get("/api/materias/")
    eventos_por_dia: dict = {}
    for evento in eventos:
        d = datetime.strptime(evento["exam_date"], "%Y-%m-%d").date()
        if d.year == ano and d.month == mes:
            eventos_por_dia.setdefault(d.day, []).append(evento)

    mes_anterior = mes - 1 if mes > 1 else 12
    ano_anterior = ano if mes > 1 else ano - 1
    proximo_mes = mes + 1 if mes < 12 else 1
    proximo_ano = ano if mes < 12 else ano + 1

    nome_mes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes - 1]

    return render_template("calendar.html", cal=cal, year=ano, month=mes,
                           month_name=nome_mes, today=hoje, exams_by_day=eventos_por_dia,
                           prev_month=mes_anterior, prev_year=ano_anterior,
                           next_month=proximo_mes, next_year=proximo_ano,
                           subjects=todas_materias)


@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    semestre_key = request.args.get("semestre_key")
    if semestre_key is not None:
        session["semestre_key"] = semestre_key
    else:
        semestre_key = session.get("semestre_key", "ativo")

    is_historico = semestre_key != "ativo"

    if request.method == "POST":
        acao = request.form.get("action")
        if acao == "create" and not is_historico:
            dados = {
                "day_of_week": int(request.form["day_of_week"]),
                "start_time": request.form["start_time"],
                "end_time": request.form["end_time"],
                "subject_id": int(request.form["subject_id"]),
            }
            _, err = api_post("/api/horarios/", dados)
            flash("Horário adicionado!" if not err else f"Erro: {err}", "success" if not err else "danger")
        elif acao == "delete" and not is_historico:
            api_delete(f"/api/horarios/{request.form['schedule_id']}")
            flash("Horário removido!", "success")
        return redirect(url_for("schedule"))

    params_sem = _params_api_semestre(semestre_key)
    semestres = _semestres_disponiveis()
    semestre_label = next((s["label"] for s in semestres if s["key"] == semestre_key), "Semestre Atual")

    todas_materias = api_get("/api/materias/")
    lista_horarios = api_get("/api/horarios/", params=params_sem)

    manha = {i: [] for i in range(7)}
    tarde = {i: [] for i in range(7)}
    noite = {i: [] for i in range(7)}
    for h in lista_horarios:
        hora = int(h["start_time"][:2])
        if hora < 12:
            manha[h["day_of_week"]].append(h)
        elif hora < 18:
            tarde[h["day_of_week"]].append(h)
        else:
            noite[h["day_of_week"]].append(h)

    return render_template("schedule.html", subjects=todas_materias,
                           morning=manha, afternoon=tarde, evening=noite, days=DAYS_PT,
                           semestres=semestres, semestre_key=semestre_key,
                           semestre_label=semestre_label, is_historico=is_historico)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
