from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/notas", tags=["Notas"])


def _calcula_situacao(notas: list, materia: models.Subject):
    notas_np = [n for n in notas if n.grade_type.startswith("NP")]
    nota_final = next((n for n in notas if n.grade_type == "Exame Final"), None)

    tipos_lancados = {n.grade_type for n in notas_np}
    nps_lancadas = len(tipos_lancados)
    nps_total = materia.num_exams

    if nps_lancadas < nps_total:
        soma_atual = sum(n.value for n in notas_np)
        nps_restantes = nps_total - nps_lancadas
        min_necessaria = round((60 * nps_total - soma_atual) / nps_restantes, 2) if nps_restantes > 0 else None
        return {
            "average": None,
            "status": None,
            "final_needed": None,
            "nota_final": None,
            "media_final": None,
            "nps_lancadas": nps_lancadas,
            "nps_total": nps_total,
            "min_necessaria": min_necessaria,
            "impossivel_aprovar": (min_necessaria is not None and min_necessaria > 100),
        }

    media = sum(n.value for n in notas_np) / nps_total if nps_total > 0 else None

    if media is None:
        status, final_needed, media_final_val = None, None, None
    elif media >= 60:
        status, final_needed, media_final_val = "aprovado", None, None
    elif media > 30:
        if nota_final is not None:
            mf = (media + nota_final.value) / 2
            media_final_val = round(mf, 2)
            status = "aprovado_final" if mf > 50 else "reprovado_final"
            final_needed = None
        else:
            status = "final"
            final_needed = round(100 - media, 2)
            media_final_val = None
    else:
        status, final_needed, media_final_val = "reprovado", None, None

    return {
        "average": round(media, 2) if media is not None else None,
        "status": status,
        "final_needed": final_needed,
        "nota_final": nota_final.value if nota_final else None,
        "media_final": media_final_val,
        "nps_lancadas": nps_lancadas,
        "nps_total": nps_total,
        "min_necessaria": None,
        "impossivel_aprovar": False,
    }


@router.get("/medias", summary="Situação de todas as matérias")
def todas_as_medias(
    arquivado: bool = Query(False),
    ano: Optional[int] = Query(None),
    semestre: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Subject).filter(models.Subject.is_arquivado == arquivado)
    if ano is not None:
        query = query.filter(models.Subject.year == ano)
    if semestre is not None:
        query = query.filter(models.Subject.semester == semestre)
    materias = query.all()
    resultado = []
    for materia in materias:
        notas = db.query(models.Grade).filter(models.Grade.subject_id == materia.id).all()
        situacao = _calcula_situacao(notas, materia)
        resultado.append({"subject_id": materia.id, "subject_name": materia.name, **situacao})
    return resultado


@router.get("/", response_model=List[schemas.GradeOut], summary="Listar notas")
def listar_notas(subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    consulta = db.query(models.Grade)
    if subject_id:
        consulta = consulta.filter(models.Grade.subject_id == subject_id)
    return consulta.all()


@router.post("/", response_model=schemas.GradeOut, status_code=201, summary="Inserir nota")
def inserir_nota(dados: schemas.GradeCreate, db: Session = Depends(get_db)):
    materia = db.query(models.Subject).filter(models.Subject.id == dados.subject_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    duplicada = db.query(models.Grade).filter(
        models.Grade.subject_id == dados.subject_id,
        models.Grade.grade_type == dados.grade_type,
    ).first()
    if duplicada:
        raise HTTPException(status_code=409, detail=f"Já existe uma nota para {dados.grade_type} nesta matéria.")
    nota = models.Grade(**dados.model_dump())
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota


@router.put("/{nota_id}", response_model=schemas.GradeOut, summary="Atualizar nota")
def atualizar_nota(nota_id: int, dados: schemas.GradeCreate, db: Session = Depends(get_db)):
    nota = db.query(models.Grade).filter(models.Grade.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    duplicada = db.query(models.Grade).filter(
        models.Grade.subject_id == dados.subject_id,
        models.Grade.grade_type == dados.grade_type,
        models.Grade.id != nota_id,
    ).first()
    if duplicada:
        raise HTTPException(status_code=409, detail=f"Já existe outra nota para {dados.grade_type} nesta matéria.")
    for campo, valor in dados.model_dump().items():
        setattr(nota, campo, valor)
    db.commit()
    db.refresh(nota)
    return nota


@router.delete("/{nota_id}", status_code=204, summary="Remover nota")
def remover_nota(nota_id: int, db: Session = Depends(get_db)):
    nota = db.query(models.Grade).filter(models.Grade.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    db.delete(nota)
    db.commit()


@router.get("/averages/all", include_in_schema=False)
def todas_as_medias_legado(db: Session = Depends(get_db)):
    return todas_as_medias(db)
