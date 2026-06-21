from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine, Base
from app.routers import subjects, grades, exams, schedules

Base.metadata.create_all(bind=engine)

# Migrações para bancos existentes — ignoradas se as colunas já existirem
_MIGRACOES = [
    "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS num_exams INTEGER NOT NULL DEFAULT 2;",
    """CREATE TABLE IF NOT EXISTS subject_nps (
        id SERIAL PRIMARY KEY,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        np_number INTEGER NOT NULL,
        weight FLOAT NOT NULL DEFAULT 1.0,
        exam_date DATE
    );""",
    "ALTER TABLE exams ADD COLUMN IF NOT EXISTS tipo_evento VARCHAR NOT NULL DEFAULT 'prova';",
    "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS is_arquivado BOOLEAN NOT NULL DEFAULT FALSE;",
]

with engine.connect() as conn:
    for sql in _MIGRACOES:
        try:
            conn.execute(text(sql))
            conn.commit()
        except Exception:
            conn.rollback()

app = FastAPI(title="API do SemestreApp", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subjects.router)
app.include_router(grades.router)
app.include_router(exams.router)
app.include_router(schedules.router)


@app.get("/")
def root():
    return {"mensagem": "API do SemestreApp", "docs": "/docs"}
