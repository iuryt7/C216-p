from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/materias", tags=["Matérias"])


def _sincronizar_nps(materia: models.Subject, db: Session):
    existentes = {np.np_number: np for np in materia.nps}
    num_nps = materia.num_exams
    for i in range(1, num_nps + 1):
        if i not in existentes:
            db.add(models.SubjectNP(subject_id=materia.id, np_number=i))
    for numero, np in list(existentes.items()):
        if numero > num_nps:
            db.delete(np)
    db.commit()
    db.refresh(materia)


@router.get("/historico", summary="Histórico de semestres arquivados")
def historico_semestres(db: Session = Depends(get_db)):
    from app.routers.grades import _calcula_situacao
    arquivadas = db.query(models.Subject).filter(models.Subject.is_arquivado == True).all()
    grupos: dict = {}
    for materia in arquivadas:
        chave = (materia.year or 0, materia.semester or 0)
        if chave not in grupos:
            grupos[chave] = []
        notas = db.query(models.Grade).filter(models.Grade.subject_id == materia.id).all()
        situacao = _calcula_situacao(notas, materia)
        grupos[chave].append({
            "nome": materia.name,
            "media": situacao.get("average"),
            "status": situacao.get("status"),
        })
    resultado = []
    for (ano, sem), materias in sorted(grupos.items(), reverse=True):
        resultado.append({"ano": ano, "semestre": sem, "materias": materias})
    return resultado


@router.get("/", response_model=List[schemas.SubjectOut], summary="Listar matérias")
def listar_materias(arquivado: bool = Query(False), db: Session = Depends(get_db)):
    return db.query(models.Subject).filter(models.Subject.is_arquivado == arquivado).all()


@router.post("/arquivar-semestre", summary="Arquivar todas as matérias ativas")
def arquivar_semestre(db: Session = Depends(get_db)):
    ativas = db.query(models.Subject).filter(models.Subject.is_arquivado == False).all()
    for m in ativas:
        m.is_arquivado = True
    db.commit()
    return {"arquivadas": len(ativas)}


@router.post("/", response_model=schemas.SubjectOut, status_code=201, summary="Criar matéria")
def criar_materia(dados: schemas.SubjectCreate, db: Session = Depends(get_db)):
    materia = models.Subject(**dados.model_dump())
    db.add(materia)
    db.commit()
    db.refresh(materia)
    _sincronizar_nps(materia, db)
    return materia


@router.get("/{materia_id}", response_model=schemas.SubjectOut, summary="Detalhar matéria")
def detalhar_materia(materia_id: int, db: Session = Depends(get_db)):
    materia = db.query(models.Subject).filter(models.Subject.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    return materia


@router.put("/{materia_id}", response_model=schemas.SubjectOut, summary="Atualizar matéria")
def atualizar_materia(materia_id: int, dados: schemas.SubjectCreate, db: Session = Depends(get_db)):
    materia = db.query(models.Subject).filter(models.Subject.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    for campo, valor in dados.model_dump().items():
        setattr(materia, campo, valor)
    db.commit()
    _sincronizar_nps(materia, db)
    return materia


@router.delete("/{materia_id}", status_code=204, summary="Remover matéria")
def remover_materia(materia_id: int, db: Session = Depends(get_db)):
    materia = db.query(models.Subject).filter(models.Subject.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    db.delete(materia)
    db.commit()


@router.get("/{materia_id}/situacao", summary="Situação de aprovação da matéria")
def situacao_materia(materia_id: int, db: Session = Depends(get_db)):
    from app.routers.grades import _calcula_situacao
    materia = db.query(models.Subject).filter(models.Subject.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    notas = db.query(models.Grade).filter(models.Grade.subject_id == materia_id).all()
    situacao = _calcula_situacao(notas, materia)
    return {"materia_id": materia_id, "nome": materia.name, **situacao}
