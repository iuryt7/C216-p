from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/horarios", tags=["Horários"])


@router.get("/", response_model=List[schemas.ScheduleOut], summary="Listar grade horária")
def listar_horarios(
    arquivado: bool = Query(False),
    ano: Optional[int] = Query(None),
    semestre: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Lista todos os horários da grade, ordenados por dia da semana e horário de início.

    - **arquivado=false** (padrão): horários de matérias do semestre ativo.
    - **arquivado=true + ano + semestre**: horários de um semestre arquivado específico.

    A convenção de dias segue: 0 = Domingo, 1 = Segunda, …, 6 = Sábado.
    Os horários são automaticamente classificados em turnos pelo frontend:
    antes das 12h (manhã), 12h–18h (tarde), a partir das 18h (noite).
    """
    query = (
        db.query(models.Schedule)
        .join(models.Subject)
        .filter(models.Subject.is_arquivado == arquivado)
    )
    if ano is not None:
        query = query.filter(models.Subject.year == ano)
    if semestre is not None:
        query = query.filter(models.Subject.semester == semestre)
    return query.order_by(models.Schedule.day_of_week, models.Schedule.start_time).all()


@router.post("/", response_model=schemas.ScheduleOut, status_code=201, summary="Adicionar horário")
def adicionar_horario(dados: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    """
    Adiciona um horário de aula semanal para uma matéria.

    - **day_of_week**: 0 (Domingo) a 6 (Sábado).
    - **start_time** / **end_time**: horários no formato `HH:MM` ou `HH:MM:SS`.
    - **subject_id**: ID da matéria à qual o horário pertence.

    Retorna 404 se a matéria não for encontrada.
    """
    materia = db.query(models.Subject).filter(models.Subject.id == dados.subject_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    horario = models.Schedule(**dados.model_dump())
    db.add(horario)
    db.commit()
    db.refresh(horario)
    return horario


@router.delete("/{horario_id}", status_code=204, summary="Remover horário")
def remover_horario(horario_id: int, db: Session = Depends(get_db)):
    """
    Remove um horário da grade semanal.

    Retorna 404 se o horário não existir.
    Retorna 204 (sem corpo) em caso de sucesso.
    """
    horario = db.query(models.Schedule).filter(models.Schedule.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horário não encontrado.")
    db.delete(horario)
    db.commit()
