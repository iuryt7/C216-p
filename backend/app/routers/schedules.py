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
    horario = db.query(models.Schedule).filter(models.Schedule.id == horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horário não encontrado.")
    db.delete(horario)
    db.commit()
