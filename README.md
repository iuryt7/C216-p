# SemestreApp — Gerenciador de Semestre Acadêmico

Aplicação web para auxiliar estudantes no gerenciamento do semestre: acompanhamento de notas por NP, grade horária, eventos no calendário, dashboard com gráfico de desempenho e histórico de semestres anteriores.

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI (Python 3.11) |
| Banco de dados | PostgreSQL 15 |
| Frontend | Flask + Jinja2 + Bootstrap 5 |
| Testes | Pytest + httpx |
| Orquestração | Docker + Docker Compose |

---

## Arquitetura

```
┌─────────────────┐        HTTP        ┌──────────────────┐        SQL        ┌──────────────┐
│  Frontend Flask │ ──────────────────▶│  Backend FastAPI  │ ────────────────▶│  PostgreSQL  │
│   porta 5000    │                    │    porta 8000     │                   │  porta 5432  │
└─────────────────┘                    └──────────────────┘                   └──────────────┘
```

O frontend **não acessa o banco diretamente** — toda lógica de negócio passa pela API REST do backend.

---

## Banco de Dados

### Diagrama de relacionamentos

```
subjects (1) ────────── (N) grades
subjects (1) ────────── (N) schedules
subjects (1) ────────── (N) subject_nps
subjects (N) ────────── (M) exams   [via exam_subjects]
```

- **N-1**: Muitas `grades` pertencem a uma `subject`
- **N-1**: Muitos `schedules` pertencem a uma `subject`
- **N-1**: Muitas `subject_nps` pertencem a uma `subject` (usadas para datas de prova)
- **N-M**: Uma `exam` pode cobrir várias `subjects`, uma `subject` pode ter várias `exams`

### Tabelas

| Tabela | Descrição |
|--------|-----------|
| `subjects` | Matérias/disciplinas (nome, professor, semestre, cor, número de NPs, flag de arquivamento) |
| `subject_nps` | NPs por matéria (número, data de prova) |
| `grades` | Notas por matéria (valor 0–100, tipo NP1/NP2/…/Exame Final, data) |
| `exams` | Provas e eventos agendados (título, data, tipo: prova/reposição/outro) |
| `exam_subjects` | Tabela de junção N-M entre eventos e matérias |
| `schedules` | Grade horária semanal (dia, horário de início/fim) |

---

## Páginas do Frontend

| URL | Descrição |
|-----|-----------|
| `/` | Dashboard: resumo do semestre (aprovadas/em risco/reprovadas), gráfico de desempenho, próximas provas, aulas de hoje e histórico de semestres |
| `/subjects` | Cadastro e gerenciamento de matérias, ordenação por nome/quantidade de NPs, histórico de semestres arquivados |
| `/grades` | Inserção e edição de notas, visualização de médias com situação de aprovação e cálculo de exame final |
| `/calendar` | Calendário mensal com provas, reposições e outros eventos |
| `/schedule` | Grade semanal de horários dividida em turnos (manhã, tarde, noite) |

### Seletor de semestre

As páginas **Dashboard** e **Grade Horária** possuem um seletor de semestre no cabeçalho. Ao alternar para um semestre arquivado:

- Apenas as matérias, notas e horários daquele semestre são exibidos
- A visualização é **somente leitura** (não é possível adicionar ou remover dados)
- Uma faixa informativa indica o modo histórico

A seleção persiste enquanto a sessão do navegador estiver ativa.

---

## API REST — Endpoints

### Matérias

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/materias/` | Listar matérias (`?arquivado=false`) |
| POST | `/api/materias/` | Criar matéria |
| GET | `/api/materias/{id}` | Detalhar matéria |
| PUT | `/api/materias/{id}` | Atualizar matéria |
| DELETE | `/api/materias/{id}` | Remover matéria |
| GET | `/api/materias/{id}/situacao` | Situação de aprovação da matéria |
| GET | `/api/materias/historico` | Semestres arquivados agrupados com médias |
| POST | `/api/materias/arquivar-semestre` | Arquivar todas as matérias ativas |

### Notas

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/notas/` | Listar notas (filtro: `?subject_id=`) |
| POST | `/api/notas/` | Inserir nota (NP1/NP2/…/Exame Final, valor 0–100) |
| PUT | `/api/notas/{id}` | Atualizar nota existente |
| DELETE | `/api/notas/{id}` | Remover nota |
| GET | `/api/notas/medias` | Situação de todas as matérias (`?arquivado=false&ano=&semestre=`) |

### Eventos (Provas e Calendário)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/eventos/` | Listar eventos (filtro: `?from_date=`) |
| POST | `/api/eventos/` | Criar evento (tipo: prova / reposição / outro) |
| PUT | `/api/eventos/{id}` | Atualizar evento |
| DELETE | `/api/eventos/{id}` | Remover evento |

### Horários

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/horarios/` | Listar grade horária (`?arquivado=false&ano=&semestre=`) |
| POST | `/api/horarios/` | Adicionar horário (0=Dom … 6=Sáb) |
| DELETE | `/api/horarios/{id}` | Remover horário |

**Total: 20 endpoints cobrindo todos os métodos REST (GET, POST, PUT, DELETE)**

---

## Como Executar

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado e em execução
- [Docker Compose](https://docs.docker.com/compose/install/) (incluso no Docker Desktop)

### 1. Clonar o repositório

```bash
git clone <url-do-repositório>
cd C216-p
```

### 2. Subir todos os serviços

```bash
docker-compose up --build
```

Na primeira execução, o Docker irá:
1. Baixar as imagens base (Python 3.11, PostgreSQL 15)
2. Instalar as dependências de cada serviço
3. Iniciar o banco de dados e aguardar o healthcheck
4. Iniciar o backend (as tabelas são criadas automaticamente via SQLAlchemy)
5. Iniciar o frontend

### 3. Acessar a aplicação

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:5000 |
| API (docs interativos) | http://localhost:8000/docs |
| API (redoc) | http://localhost:8000/redoc |

### 4. Rodar em modo background

```bash
docker-compose up --build -d
```

Para ver os logs:

```bash
docker-compose logs -f
```

### 5. Parar os serviços

```bash
docker-compose down
```

Para remover também o volume do banco de dados (apaga todos os dados):

```bash
docker-compose down -v
```

---

## Como Executar os Testes

Os testes usam SQLite em memória — não requerem o PostgreSQL rodando.

### Opção 1: Dentro do container (recomendado)

```bash
# Com os serviços já rodando:
docker-compose exec backend pytest tests/ -v

# Sem precisar subir os outros serviços:
docker-compose run --rm backend pytest tests/ -v
```

### Opção 2: Local (requer Python 3.11+)

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Boas Práticas de Uso

### Fluxo sugerido para um novo semestre

1. **Cadastre as matérias** em `/subjects` com professor, cor identificadora e número de NPs
2. **Monte a grade horária** em `/schedule` com os dias e horários de cada aula
3. **Agende provas e reposições** diretamente pelo Calendário em `/calendar`
4. **Registre suas notas** em `/grades` conforme as avaliações acontecem
5. **Acompanhe o dashboard** em `/` para ver o gráfico de desempenho e a situação por matéria
6. Ao fim do semestre, **arquive todas as matérias** em `/subjects` com o botão "Arquivar Semestre"

### Convenções de notas

- Notas válidas: **0 a 100** (a API rejeita valores fora desse intervalo)
- Tipos de avaliação: **NP1, NP2, NP3…** e **Exame Final** — sem duplicatas por matéria
- A **média final** é calculada somente quando todas as NPs da matéria foram lançadas:
  - Média **≥ 60** → Aprovado
  - **30 < média < 60** → Exame Final (a nota mínima necessária é exibida)
  - Média **≤ 30** → Reprovado direto
- Se o aluno fizer o Exame Final: **(média NP + nota final) / 2 > 50** → Aprovado via Final
- Enquanto nem todas as NPs foram lançadas, o sistema mostra a **nota mínima necessária** nas NPs restantes para aprovação

### Histórico de semestres

- Use "Arquivar Semestre" para encerrar o semestre atual e começar um novo
- As matérias arquivadas ficam visíveis em `/subjects` (seção recolhível) e no dashboard
- No Dashboard e na Grade Horária, use o **seletor de semestre** no canto superior direito para alternar entre o semestre atual e os anteriores

### Gerenciamento via API

A documentação interativa em `http://localhost:8000/docs` permite testar todos os endpoints diretamente no navegador. É especialmente útil para:
- Inspecionar as respostas completas da API
- Realizar buscas filtradas por data, matéria ou semestre
- Testar validações (notas fora do intervalo, datas inválidas, etc.)

---

## Estrutura do Projeto

```
C216-p/
├── backend/
│   ├── app/
│   │   ├── main.py          # Entrypoint FastAPI + migrações de esquema
│   │   ├── database.py      # Configuração SQLAlchemy
│   │   ├── models.py        # Modelos ORM (Subject, Grade, Exam, Schedule, SubjectNP)
│   │   ├── schemas.py       # Schemas Pydantic (validação de entrada/saída)
│   │   └── routers/
│   │       ├── subjects.py  # CRUD de matérias + arquivamento de semestre
│   │       ├── grades.py    # CRUD de notas + cálculo de médias e situação
│   │       ├── exams.py     # CRUD de eventos (prova/reposição/outro)
│   │       └── schedules.py # Grade horária com filtro por semestre
│   ├── tests/
│   │   ├── conftest.py      # Fixtures do pytest (banco SQLite em memória)
│   │   ├── test_subjects.py # Testes de matérias e arquivamento
│   │   ├── test_grades.py   # Testes de notas, médias, situação e exame final
│   │   └── test_exams.py    # Testes de eventos e calendário
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py               # Aplicação Flask (5 rotas + seletor de semestre via sessão)
│   ├── templates/           # HTML com Jinja2 + Bootstrap 5
│   │   ├── base.html
│   │   ├── home.html        # Dashboard com Chart.js + seletor de semestre
│   │   ├── subjects.html    # CRUD de matérias + histórico arquivado + ordenação
│   │   ├── grades.html      # Notas, edição e situação de aprovação (incl. exame final)
│   │   ├── calendar.html    # Calendário mensal com eventos
│   │   └── schedule.html    # Grade semanal por turno + seletor de semestre
│   ├── static/style.css
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Variáveis de Ambiente

Todas configuradas no `docker-compose.yml` — não é necessário criar arquivo `.env`:

| Variável | Serviço | Valor |
|----------|---------|-------|
| `DATABASE_URL` | backend | `postgresql://student:student123@db:5432/semester_db` |
| `BACKEND_URL` | frontend | `http://backend:8000` |
| `POSTGRES_USER` | db | `student` |
| `POSTGRES_PASSWORD` | db | `student123` |
| `POSTGRES_DB` | db | `semester_db` |
