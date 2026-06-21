from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/eventos", tags=["Provas e Eventos"])


@router.get("/", response_model=List[schemas.ExamOut], summary="Listar eventos do calendário")
def listar_eventos(from_date: Optional[date] = None, db: Session = Depends(get_db)):
    """
    Lista todos os eventos agendados (provas, reposições e outros), ordenados por data.

    - **from_date** (opcional): filtra eventos a partir desta data (formato `YYYY-MM-DD`).
      Útil para buscar apenas os próximos eventos.

    Cada evento inclui a lista de matérias associadas (`subjects`).
    Tipos possíveis: `prova`, `reposicao`, `outro`.
    """
    consulta = db.query(models.Exam)
    if from_date:
        consulta = consulta.filter(models.Exam.exam_date >= from_date)
    return consulta.order_by(models.Exam.exam_date).all()


@router.post("/", response_model=schemas.ExamOut, status_code=201, summary="Criar evento no calendário")
def criar_evento(dados: schemas.ExamCreate, db: Session = Depends(get_db)):
    """
    Cria um novo evento no calendário e o associa a uma ou mais matérias.

    - **title**: título exibido no calendário.
    - **exam_date**: data do evento no formato `YYYY-MM-DD`.
    - **tipo_evento**: `prova` | `reposicao` | `outro`.
    - **subject_ids**: lista de IDs das matérias relacionadas (pode ser vazia).

    Para eventos do tipo `prova` ou `reposicao`, o título é normalmente
    preenchido automaticamente com o nome da matéria pelo frontend.
    """
    evento = models.Exam(
        title=dados.title,
        exam_date=dados.exam_date,
        description=dados.description,
        tipo_evento=dados.tipo_evento,
    )
    if dados.subject_ids:
        materias = db.query(models.Subject).filter(models.Subject.id.in_(dados.subject_ids)).all()
        evento.subjects = materias
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


@router.put("/{evento_id}", response_model=schemas.ExamOut, summary="Atualizar evento")
def atualizar_evento(evento_id: int, dados: schemas.ExamUpdate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de um evento existente, incluindo as matérias associadas.

    - A lista `subject_ids` substitui completamente as associações anteriores.
    - Para remover todas as matérias de um evento, envie `subject_ids: []`.

    Retorna 404 se o evento não for encontrado.
    """
    evento = db.query(models.Exam).filter(models.Exam.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    evento.title = dados.title
    evento.exam_date = dados.exam_date
    evento.description = dados.description
    evento.tipo_evento = dados.tipo_evento
    if dados.subject_ids is not None:
        materias = db.query(models.Subject).filter(models.Subject.id.in_(dados.subject_ids)).all()
        evento.subjects = materias
    db.commit()
    db.refresh(evento)
    return evento


@router.delete("/{evento_id}", status_code=204, summary="Remover evento")
def remover_evento(evento_id: int, db: Session = Depends(get_db)):
    """
    Remove permanentemente um evento do calendário.

    Retorna 404 se o evento não existir.
    Retorna 204 (sem corpo) em caso de sucesso.
    """
    evento = db.query(models.Exam).filter(models.Exam.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    db.delete(evento)
    db.commit()
