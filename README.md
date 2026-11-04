# Backend — LLM Contábil/Tributário

API FastAPI do projeto: expõe o chat (RAG + Ollama), as calculadoras
determinísticas de tributos/contabilidade, o upload/análise de documentos e
os dados da base de legislação. Não contém o núcleo de IA (embeddings,
Chroma, busca híbrida, cliente do Ollama) — isso vive em `../ai-engine/` e é
consumido daqui só através de `ai_engine.client` (ver "Arquitetura", abaixo).

## Arquitetura

Este pacote é a metade "backend" da divisão lógica `backend/` + `ai-engine/`
decidida na governança arquitetural de 2026-11-04 (ver
`../docs/architecture/AUDIT_REPORT.md`, §7). Hoje os dois pacotes rodam no
mesmo processo Python (sem rede entre eles); a única regra que importa no
dia a dia é: **código daqui nunca importa de `ai_engine.retrieval`,
`ai_engine.vector_store` ou `ai_engine.llm_client` diretamente — só de
`ai_engine.client`**, que é a fachada estável. Isso é o que vai permitir
trocar "import direto" por "chamada HTTP" no futuro (fase de
infraestrutura/Docker) sem reescrever o backend.

```
backend/
├── app/
│   ├── main.py              # FastAPI app, todas as rotas e modelos Pydantic
│   ├── chat_service.py      # orquestra retrieval (ai_engine.client) + geração
│   ├── config.py            # Settings do backend (armazenamento de documentos)
│   └── interface/
│       └── streamlit_app.py # interface alternativa de debug (não é o produto)
├── taxation/                 # calculadoras tributárias determinísticas
├── accounting/                # calculadoras contábeis determinísticas
├── documents/                 # upload/extração/análise de documentos do usuário
├── tests/                     # pytest (50 testes)
├── run.ps1 / run.sh           # atalho pra subir a API com o PYTHONPATH certo
└── README.md                  # este arquivo
```

## Módulos

- **`app/`** — a API em si. `main.py` tem todas as rotas (ver lista abaixo);
  `chat_service.py` monta o prompt com as regras de confiabilidade (nunca
  inventar artigo/alíquota/pronunciamento, sempre citar fonte + data de
  referência, declarar quando não há evidência suficiente) e chama
  `ai_engine.client.hybrid_search` + `ai_engine.client.chat`/`stream_chat`.
- **`taxation/`** — Simples Nacional (Anexos I-V + Fator R), Lucro Presumido
  (com a majoração trimestral proporcional de R$ 1.250.000 + carryforward,
  IN RFB 2305/2025 e 2306/2026), Lucro Real simplificado, comparador de
  regimes, simulação de IBS/CBS (fase de testes 2026). Tabelas de alíquotas
  em `taxation/rates.py`, cada uma com `fonte` e `vigencia_inicio`.
- **`accounting/`** — Balanço Patrimonial (com validação da equação
  contábil), DRE, DFC (CPC 03 (R2)), indicadores de liquidez/endividamento/
  rentabilidade/EBITDA, análise vertical/horizontal.
- **`documents/`** — upload (PDF/DOCX/XLSX/CSV/XML/TXT), extração de texto
  (PDF via `ai_engine.client.extract_text_from_pdf`; os demais formatos são
  extraídos aqui mesmo), análise por IA (reaproveita
  `ai_engine.client.chat`), e persistência local em
  `../database/documents/` (índice JSON — **não é seguro para escrita
  concorrente entre processos**, é suficiente só para o uso local atual de
  um único processo uvicorn).
- **`tests/`** — 50 testes pytest. `test_api.py` usa `TestClient(app)`;
  `test_documents.py` isola o módulo `documents.storage` com `monkeypatch`
  (estado em módulo, não por-instância); `test_chat_stream.py` testa o SSE
  sem precisar do Ollama de verdade (mocka a geração).

## Rotas da API

```
GET    /health
GET    /legislation/sources
GET    /legislation/sources/{fonte_id}/content
GET    /taxation/reform-timeline
POST   /taxation/ibs-cbs-simulacao
POST   /accounting/balance-sheet
POST   /accounting/income-statement
POST   /accounting/cash-flow
POST   /accounting/financial-indicators
POST   /accounting/horizontal-analysis
POST   /documents/upload
GET    /documents
GET    /documents/{doc_id}
GET    /documents/{doc_id}/text
POST   /documents/{doc_id}/analyze
DELETE /documents/{doc_id}
POST   /chat
GET    /chat/stream          # SSE: eventos "sources", "token", "done", "stream_error"
```

Docs interativas em `/docs` (Swagger) e `/redoc` enquanto o servidor estiver
rodando. CORS liberado só para `http://localhost:3000` (o frontend Next.js),
métodos `GET`/`POST`/`DELETE`.

## Como rodar

Pré-requisitos: ambiente virtual da raiz do projeto já criado e ativado
(`../.venv`), dependências instaladas (`pip install -r ../requirements.txt`),
Ollama instalado e rodando (`ollama serve` ou já em segundo plano), e a base
documental já indexada (`cd ../ai-engine && PYTHONPATH=. python -m
ai_engine.ingestion` — só precisa rodar uma vez).

Este pacote sozinho **não roda** sem `ai-engine/` no `PYTHONPATH`, porque
`app/chat_service.py`, `app/main.py` e `documents/` importam
`ai_engine.client`.

### Opção simples

```powershell
.\run.ps1
```

```bash
./run.sh
```

Os dois scripts fazem a mesma coisa: setam `PYTHONPATH=../ai-engine` e
chamam `uvicorn app.main:app --reload`.

### Manual (PowerShell)

```powershell
$env:PYTHONPATH = "../ai-engine"
uvicorn app.main:app --reload
```

### Manual (Git Bash)

```bash
PYTHONPATH="../ai-engine" uvicorn app.main:app --reload
```

Depois de subir: `POST http://localhost:8000/chat` com
`{"question": "O que é o IBS?"}`, ou abra `http://localhost:8000/docs`.

### Interface Streamlit (alternativa de debug)

```powershell
$env:PYTHONPATH = ".;../ai-engine"
streamlit run app/interface/streamlit_app.py
```

## Testes

```powershell
$env:PYTHONPATH = ".;../ai-engine"
python -m pytest tests/ -v
```

```bash
PYTHONPATH=".;../ai-engine" python -m pytest tests/ -v
```

Os testes de `taxation/`/`accounting`/`documents` não precisam de rede nem
do Ollama. `test_api.py` e `test_chat_stream.py` usam `TestClient` e mockam
a geração — não fazem chamada real ao Ollama (por isso passam mesmo sem ele
instalado). Para validar a geração de verdade, é preciso o servidor rodando
e o Ollama de pé (ver `../README.md`, seção "Limitações conhecidas").

## Limitações conhecidas (específicas do backend)

- `documents/storage.py` usa um índice JSON local, não um banco de dados —
  não suporta múltiplos processos escrevendo ao mesmo tempo, e não tem
  controle de concorrência. Suficiente para um único usuário local; não é
  adequado para produção multi-usuário.
- `app/interface/streamlit_app.py` é uma ferramenta de debug interna,
  redundante com o frontend Next.js real (`../frontend/`). Seu destino
  (manter ou remover) ainda não foi decidido — ver
  `../docs/architecture/AUDIT_REPORT.md`.
- Não há autenticação/autorização nem conceito de usuário/empresa — todas
  as rotas são públicas, pensadas para uso local de um único usuário.
- `taxation/` não cobre ISS/ICMS (variam por município/estado) e o Lucro
  Real é simplificado (sem LALUR completo). Ver detalhes e datas de
  verificação das tabelas em `../README.md`.
