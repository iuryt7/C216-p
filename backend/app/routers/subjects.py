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
    """
    Retorna todos os semestres arquivados, agrupados por ano e semestre,
    com a situação de aprovação calculada para cada matéria.

    Cada grupo contém:
    - `ano` e `semestre` do grupo.
    - `materias`: lista com `nome`, `media` e `status` de cada matéria arquivada.

    Ordenado do semestre mais recente ao mais antigo.
    """
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
    """
    Lista matérias filtrando por situação de arquivamento.

    - **arquivado=false** (padrão): retorna apenas as matérias do semestre ativo.
    - **arquivado=true**: retorna todas as matérias de semestres já arquivados.

    Cada matéria inclui a lista de NPs com número e data de prova.
    """
    return db.query(models.Subject).filter(models.Subject.is_arquivado == arquivado).all()


@router.post("/arquivar-semestre", summary="Arquivar todas as matérias ativas")
def arquivar_semestre(db: Session = Depends(get_db)):
    """
    Marca todas as matérias ativas (`is_arquivado=false`) como arquivadas.

    Use ao encerrar o semestre letivo para preservar o histórico e liberar
    o sistema para cadastrar as matérias do próximo semestre.

    Retorna `{ "arquivadas": N }` com o número de matérias afetadas.
    """
    ativas = db.query(models.Subject).filter(models.Subject.is_arquivado == False).all()
    for m in ativas:
        m.is_arquivado = True
    db.commit()
    return {"arquivadas": len(ativas)}


@router.post("/", response_model=schemas.SubjectOut, status_code=201, summary="Criar matéria")
def criar_materia(dados: schemas.SubjectCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova matéria no semestre ativo e gera automaticamente os registros
    de NP correspondentes ao `num_exams` informado.

    - **num_exams**: quantidade de avaliações parciais (NP1, NP2, …). Padrão: 2.
    - **color_hex**: cor de identificação visual no formato `#RRGGBB`. Padrão: `#4f46e5`.
    - **semester**: 1 ou 2 (semestre letivo dentro do ano).
    """
    materia = models.Subject(**dados.model_dump())
    db.add(materia)
    db.commit()
    db.refresh(materia)
    _sincronizar_nps(materia, db)
    return materia


@router.get("/{materia_id}", response_model=schemas.SubjectOut, summary="Detalhar matéria")
def detalhar_materia(materia_id: int, db: Session = Depends(get_db)):
    """
    Retorna os dados completos de uma matéria, incluindo a lista de NPs com datas de prova.

    Retorna 404 se a matéria não for encontrada.
    """
    materia = db.query(models.Subject).filter(models.Subject.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    return materia


@router.put("/{materia_id}", response_model=schemas.SubjectOut, summary="Atualizar matéria")
def atualizar_materia(materia_id: int, dados: schemas.SubjectCreate, db: Session = Depends(get_db)):
    """
    Atualiza os dados de uma matéria existente.

    Se `num_exams` mudar, os registros de NP são sincronizados automaticamente:
    NPs excedentes são removidas e novas são criadas para os números que faltam.
    As NPs existentes (e suas datas) são preservadas.
    """
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
    """
    Remove permanentemente uma matéria e todos os dados associados
    (notas, horários, NPs e vínculos com eventos).

    Retorna 204 (sem corpo) em caso de sucesso.
    """
    materia = db.query(models.Subject).filter(models.Subject.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    db.delete(materia)
    db.commit()


@router.get("/{materia_id}/situacao", summary="Situação de aprovação da matéria")
def situacao_materia(materia_id: int, db: Session = Depends(get_db)):
    """
    Calcula e retorna a situação de aprovação atual de uma matéria específica.

    Regras de aprovação:
    - Média NP ≥ 60 → **aprovado**
    - 30 < Média NP < 60 → **final** (aguardando Exame Final)
    - Média NP ≤ 30 → **reprovado**
    - Com Exame Final: (Média NP + Exame Final) / 2 > 50 → **aprovado_final**

    Inclui `min_necessaria` (nota mínima nas NPs restantes) quando nem todas foram lançadas.
    """
    from app.routers.grades import _calcula_situacao
    materia = db.query(models.Subject).filter(models.Subject.id == materia_id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria não encontrada.")
    notas = db.query(models.Grade).filter(models.Grade.subject_id == materia_id).all()
    situacao = _calcula_situacao(notas, materia)
    return {"materia_id": materia_id, "nome": materia.name, **situacao}
