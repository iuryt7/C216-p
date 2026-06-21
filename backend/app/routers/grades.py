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
    """
    Retorna a situação de aprovação de cada matéria do semestre selecionado.

    - **arquivado=false** (padrão): somente matérias do semestre ativo.
    - **arquivado=true + ano + semestre**: matérias de um semestre arquivado específico.

    Cada item retorna:
    - `average`: média simples das NPs lançadas (null se incompleto).
    - `status`: `aprovado` | `final` | `reprovado` | `aprovado_final` | `reprovado_final` | null.
    - `final_needed`: nota mínima necessária no Exame Final para aprovação.
    - `nota_final` / `media_final`: resultado do Exame Final quando lançado.
    - `min_necessaria`: nota mínima nas NPs restantes para ainda poder passar.
    - `impossivel_aprovar`: true se mesmo com 100 nas NPs restantes não é possível atingir 60.
    """
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
def listar_notas(
    subject_id: Optional[int] = None,
    arquivado: bool = Query(False),
    ano: Optional[int] = Query(None),
    semestre: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Lista todas as notas lançadas, com filtro opcional por matéria e semestre.

    - **subject_id**: filtra notas de uma única matéria.
    - **arquivado=false** (padrão): notas de matérias do semestre ativo.
    - **arquivado=true + ano + semestre**: notas de um semestre arquivado específico.

    Cada nota inclui os dados completos da matéria associada (`subject`).
    """
    consulta = (
        db.query(models.Grade)
        .join(models.Subject)
        .filter(models.Subject.is_arquivado == arquivado)
    )
    if ano is not None:
        consulta = consulta.filter(models.Subject.year == ano)
    if semestre is not None:
        consulta = consulta.filter(models.Subject.semester == semestre)
    if subject_id:
        consulta = consulta.filter(models.Grade.subject_id == subject_id)
    return consulta.all()


@router.post("/", response_model=schemas.GradeOut, status_code=201, summary="Inserir nota")
def inserir_nota(dados: schemas.GradeCreate, db: Session = Depends(get_db)):
    """
    Insere uma nota para uma matéria.

    - **grade_type**: `NP1`, `NP2`, `NP3`… ou `Exame Final`.
    - **value**: valor de 0 a 100.
    - Retorna 409 se já existir nota do mesmo tipo para a mesma matéria.
    - O tipo `Exame Final` só altera a situação quando todas as NPs da matéria já foram lançadas
      e a média NP ficou entre 30 e 60 (condição de exame final).
    """
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
    """
    Atualiza valor, data, observação ou tipo de uma nota já lançada.

    - Retorna 404 se a nota não existir.
    - Retorna 409 se já existir outra nota do mesmo tipo na mesma matéria (duplicata).
    """
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
    """
    Remove permanentemente uma nota lançada.

    - Retorna 404 se a nota não existir.
    - Retorna 204 (sem corpo) em caso de sucesso.
    """
    nota = db.query(models.Grade).filter(models.Grade.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    db.delete(nota)
    db.commit()


@router.get("/averages/all", include_in_schema=False)
def todas_as_medias_legado(db: Session = Depends(get_db)):
    return todas_as_medias(db=db)
