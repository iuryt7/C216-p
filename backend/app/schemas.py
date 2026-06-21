from datetime import date, time
from typing import Optional, List
from pydantic import BaseModel, field_validator


class SubjectNPOut(BaseModel):
    id: int
    np_number: int
    weight: float
    exam_date: Optional[date] = None

    model_config = {"from_attributes": True}


class SubjectBase(BaseModel):
    name: str
    teacher: Optional[str] = None
    color_hex: Optional[str] = "#4f46e5"
    semester: Optional[int] = None
    year: Optional[int] = None
    num_exams: int = 2
    is_arquivado: bool = False


class SubjectCreate(SubjectBase):
    pass


class SubjectOut(SubjectBase):
    id: int
    nps: List[SubjectNPOut] = []

    model_config = {"from_attributes": True}


class GradeBase(BaseModel):
    value: float
    grade_type: str
    date: date
    description: Optional[str] = None
    subject_id: int

    @field_validator("value")
    @classmethod
    def value_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Nota deve estar entre 0 e 100")
        return v


class GradeCreate(GradeBase):
    pass


class GradeOut(GradeBase):
    id: int
    subject: SubjectOut

    model_config = {"from_attributes": True}


class ExamBase(BaseModel):
    title: str
    exam_date: date
    description: Optional[str] = None
    tipo_evento: str = "prova"

    @field_validator("tipo_evento")
    @classmethod
    def tipo_valido(cls, v):
        if v not in ("prova", "reposicao", "outro"):
            raise ValueError("tipo_evento deve ser 'prova', 'reposicao' ou 'outro'")
        return v


class ExamCreate(ExamBase):
    subject_ids: List[int] = []


class ExamUpdate(ExamBase):
    subject_ids: List[int] = []


class ExamOut(ExamBase):
    id: int
    subjects: List[SubjectOut] = []

    model_config = {"from_attributes": True}


class ScheduleBase(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
    subject_id: int

    @field_validator("day_of_week")
    @classmethod
    def day_range(cls, v):
        if not 0 <= v <= 6:
            raise ValueError("day_of_week deve ser entre 0 (Domingo) e 6 (Sábado)")
        return v


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleOut(ScheduleBase):
    id: int
    subject: SubjectOut

    model_config = {"from_attributes": True}
