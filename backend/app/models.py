from sqlalchemy import Column, Integer, String, Float, Date, Time, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

exam_subjects = Table(
    "exam_subjects",
    Base.metadata,
    Column("exam_id", Integer, ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True),
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True),
)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    teacher = Column(String)
    color_hex = Column(String, default="#4f46e5")
    semester = Column(Integer)
    year = Column(Integer)
    num_exams = Column(Integer, default=2, nullable=False)
    is_arquivado = Column(Boolean, default=False, nullable=False)

    grades = relationship("Grade", back_populates="subject", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="subject", cascade="all, delete-orphan")
    exams = relationship("Exam", secondary=exam_subjects, back_populates="subjects")
    nps = relationship("SubjectNP", back_populates="subject", cascade="all, delete-orphan",
                       order_by="SubjectNP.np_number")


class SubjectNP(Base):
    __tablename__ = "subject_nps"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    np_number = Column(Integer, nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    exam_date = Column(Date, nullable=True)

    subject = relationship("Subject", back_populates="nps")


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(Float, nullable=False)
    grade_type = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    subject = relationship("Subject", back_populates="grades")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    exam_date = Column(Date, nullable=False)
    description = Column(String)
    tipo_evento = Column(String, default="prova", nullable=False)

    subjects = relationship("Subject", secondary=exam_subjects, back_populates="exams")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    subject = relationship("Subject", back_populates="schedules")
