"""API FastAPI do MVP: chat com RAG sobre a base documental contábil/tributária."""
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from accounting.balance_sheet import BalancoPatrimonial
from accounting.cash_flow import DFC
from accounting.financial_analysis import (
    analise_horizontal,
    analise_vertical,
    indicadores_endividamento,
    indicadores_liquidez,
    indicadores_rentabilidade,
)
from accounting.income_statement import DRE
from ai_engine.client import count as vector_count
from ai_engine.client import get_chunks_by_fonte_id, load_manifest
from app.chat_service import answer_question, stream_answer_question
from app.config import settings
from documents import storage as documents_storage
from documents.analysis import analyze_document_text
from documents.extraction import FORMATOS_SUPORTADOS, formato_por_extensao
from taxation.tax_reform import proximos_marcos, simular_ibs_cbs_teste_2026

app = FastAPI(title="LLM Contábil/Tributário — MVP RAG")


def _clean_validation_message(exc: ValidationError) -> str:
    """Extrai só as mensagens de erro, sem o dump técnico (tipo/input/URL do
    pydantic) que `str(ValidationError)` inclui por padrão."""
    mensagens = []
    for erro in exc.errors():
        msg = str(erro["msg"])
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        mensagens.append(msg)
    return "; ".join(mensagens)

# Dev: libera o frontend Next.js local. Restringir em produção.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    top_k: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    reference_date: str
    context_found: bool


class LegislationSourceResponse(BaseModel):
    fonte_id: str
    titulo: str
    tipo_norma: str
    numero: str | None = None
    ano: int | None = None
    orgao_emissor: str
    data_publicacao: str | None = None
    status: str
    assunto: str
    url_fonte: str


class LegislationChunkResponse(BaseModel):
    chunk_index: int
    artigo: str | None = None
    paragrafo: str | None = None
    inciso: str | None = None
    text: str


class LegislationContentResponse(BaseModel):
    fonte_id: str
    titulo: str
    status: str
    url_fonte: str
    total_chunks: int
    chunks: list[LegislationChunkResponse]


class ReformTimelineMarcoResponse(BaseModel):
    periodo: str
    descricao: str
    status: str
    fonte: str


class IbsCbsSimulationRequest(BaseModel):
    valor_operacao: float = Field(ge=0)
    optante_simples: bool = False


class IbsCbsSimulationResponse(BaseModel):
    valor_operacao: float
    cbs: float
    ibs_estadual: float
    ibs_municipal: float
    total_ibs_cbs: float
    aplica_simples_nacional: bool
    observacao: str
    fonte: str


class BalancoPatrimonialRequest(BaseModel):
    ativo_circulante: float
    ativo_realizavel_longo_prazo: float = 0.0
    ativo_imobilizado: float = 0.0
    ativo_intangivel: float = 0.0
    ativo_investimentos: float = 0.0
    passivo_circulante: float
    passivo_nao_circulante: float = 0.0
    patrimonio_liquido: float
    estoques: float = 0.0
    disponivel: float = 0.0


class DREFieldsRequest(BaseModel):
    receita_bruta: float
    deducoes_receita: float = 0.0
    custo_produtos_vendidos: float = 0.0
    despesas_operacionais: float = 0.0
    resultado_financeiro: float = 0.0
    depreciacao_amortizacao: float = 0.0
    irpj_csll: float = 0.0


class DFCRequest(BaseModel):
    fluxo_operacional: float
    fluxo_investimento: float = 0.0
    fluxo_financiamento: float = 0.0
    caixa_inicial: float = 0.0


class DFCResponse(BaseModel):
    fluxo_operacional: float
    fluxo_investimento: float
    fluxo_financiamento: float
    variacao_caixa: float
    caixa_inicial: float
    caixa_final: float


class BalanceSheetAnalysisResponse(BaseModel):
    ativo_total: float
    ativo_nao_circulante: float
    passivo_total_exigivel: float
    liquidez_corrente: float | None
    liquidez_seca: float | None
    liquidez_geral: float | None
    liquidez_imediata: float | None
    endividamento_geral: float | None
    composicao_endividamento: float | None
    imobilizacao_patrimonio_liquido: float | None
    analise_vertical: dict[str, float | None]


class IncomeStatementAnalysisResponse(BaseModel):
    receita_liquida: float
    lucro_bruto: float
    lucro_operacional: float
    lucro_antes_ir_csll: float
    lucro_liquido: float
    ebitda: float
    analise_vertical: dict[str, float | None]


class FinancialIndicatorsResponse(BaseModel):
    liquidez_corrente: float | None
    liquidez_seca: float | None
    liquidez_geral: float | None
    liquidez_imediata: float | None
    endividamento_geral: float | None
    composicao_endividamento: float | None
    imobilizacao_patrimonio_liquido: float | None
    margem_bruta: float | None
    margem_operacional: float | None
    margem_liquida: float | None
    margem_ebitda: float | None
    roe: float | None
    roa: float | None
    ebitda: float


class HorizontalAnalysisRequest(BaseModel):
    valores_periodo_atual: dict[str, float]
    valores_periodo_anterior: dict[str, float]


class DocumentResponse(BaseModel):
    id: str
    filename: str
    formato: str
    size_bytes: int
    uploaded_at: str
    status: str
    error_message: str | None = None
    extracted_chars: int
    text_preview: str
    analysis: str | None = None
    analysis_error: str | None = None


class DocumentTextResponse(BaseModel):
    id: str
    text: str


class DocumentAnalysisResponse(BaseModel):
    id: str
    analysis: str | None
    analysis_error: str | None


def _to_document_response(record: documents_storage.DocumentRecord) -> DocumentResponse:
    return DocumentResponse(**record.__dict__)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "chunks_indexados": vector_count()}


@app.get("/legislation/sources", response_model=list[LegislationSourceResponse])
def legislation_sources() -> list[LegislationSourceResponse]:
    """Lista os documentos do manifesto (sources.yaml) — dados reais já
    coletados pelo pipeline de ingestão, usados no painel de atualizações
    legislativas do dashboard."""
    manifest = load_manifest()
    return [
        LegislationSourceResponse(
            fonte_id=doc["fonte_id"],
            titulo=doc["titulo"],
            tipo_norma=doc["tipo_norma"],
            numero=str(doc.get("numero")) if doc.get("numero") else None,
            ano=doc.get("ano"),
            orgao_emissor=doc["orgao_emissor"],
            data_publicacao=(
                doc["data_publicacao"].isoformat() if doc.get("data_publicacao") else None
            ),
            status=doc["status"],
            assunto=doc["assunto"],
            url_fonte=doc["url_fonte"],
        )
        for doc in manifest
    ]


@app.get("/legislation/sources/{fonte_id}/content", response_model=LegislationContentResponse)
def legislation_source_content(fonte_id: str) -> LegislationContentResponse:
    """Conteúdo indexado de uma norma, em ordem, para o visualizador de
    artigos (navegação sequencial). Não há histórico de versões/comparação
    — cada reingestão sobrescreve a anterior (ver limitações no README)."""
    chunks = get_chunks_by_fonte_id(fonte_id)
    if not chunks:
        raise HTTPException(status_code=404, detail=f"fonte_id '{fonte_id}' não encontrada")

    primeiro = chunks[0]
    return LegislationContentResponse(
        fonte_id=fonte_id,
        titulo=primeiro.get("titulo", ""),
        status=primeiro.get("status", "desconhecido"),
        url_fonte=primeiro.get("url_fonte", ""),
        total_chunks=len(chunks),
        chunks=[
            LegislationChunkResponse(
                chunk_index=c.get("chunk_index", 0),
                artigo=c.get("artigo") or None,
                paragrafo=c.get("paragrafo") or None,
                inciso=c.get("inciso") or None,
                text=c["text"],
            )
            for c in chunks
        ],
    )


@app.get("/taxation/reform-timeline", response_model=list[ReformTimelineMarcoResponse])
def taxation_reform_timeline() -> list[ReformTimelineMarcoResponse]:
    """Cronograma de transição da Reforma Tributária — ver
    taxation/tax_reform.py::proximos_marcos() para a distinção entre marcos
    vigentes e marcos ainda não confirmados em norma."""
    return [ReformTimelineMarcoResponse(**marco) for marco in proximos_marcos()]


@app.post("/taxation/ibs-cbs-simulacao", response_model=IbsCbsSimulationResponse)
def taxation_ibs_cbs_simulacao(req: IbsCbsSimulationRequest) -> IbsCbsSimulationResponse:
    """Simula o IBS/CBS da fase de testes de 2026 (LC 214/2025, arts. 343 e
    346) sobre um valor de operação informado. Cobre apenas 2026 — ver
    taxation/tax_reform.py para o porquê do cronograma pós-2026 não ser
    simulado aqui (depende de regulamentação não totalmente verificada)."""
    resultado = simular_ibs_cbs_teste_2026(req.valor_operacao, req.optante_simples)
    return IbsCbsSimulationResponse(
        valor_operacao=resultado.valor_operacao,
        cbs=resultado.cbs,
        ibs_estadual=resultado.ibs_estadual,
        ibs_municipal=resultado.ibs_municipal,
        total_ibs_cbs=resultado.total_ibs_cbs,
        aplica_simples_nacional=resultado.aplica_simples_nacional,
        observacao=resultado.observacao,
        fonte=resultado.fonte,
    )


@app.post("/accounting/balance-sheet", response_model=BalanceSheetAnalysisResponse)
def accounting_balance_sheet(req: BalancoPatrimonialRequest) -> BalanceSheetAnalysisResponse:
    """Analisa um Balanço Patrimonial: totais, liquidez, endividamento e
    análise vertical (cada conta como % do ativo total). A validação da
    equação contábil (Ativo = Passivo + PL) acontece aqui — ver
    accounting/balance_sheet.py::valida_equacao_contabil."""
    try:
        bp = BalancoPatrimonial(**req.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_clean_validation_message(exc)) from exc

    liquidez = indicadores_liquidez(bp)
    endividamento = indicadores_endividamento(bp)
    vertical = analise_vertical(
        {
            "ativo_circulante": bp.ativo_circulante,
            "ativo_nao_circulante": bp.ativo_nao_circulante,
            "passivo_circulante": bp.passivo_circulante,
            "passivo_nao_circulante": bp.passivo_nao_circulante,
            "patrimonio_liquido": bp.patrimonio_liquido,
        },
        base=bp.ativo_total,
    )
    return BalanceSheetAnalysisResponse(
        ativo_total=bp.ativo_total,
        ativo_nao_circulante=bp.ativo_nao_circulante,
        passivo_total_exigivel=bp.passivo_total_exigivel,
        liquidez_corrente=liquidez.liquidez_corrente,
        liquidez_seca=liquidez.liquidez_seca,
        liquidez_geral=liquidez.liquidez_geral,
        liquidez_imediata=liquidez.liquidez_imediata,
        endividamento_geral=endividamento.endividamento_geral,
        composicao_endividamento=endividamento.composicao_endividamento,
        imobilizacao_patrimonio_liquido=endividamento.imobilizacao_patrimonio_liquido,
        analise_vertical=vertical,
    )


@app.post("/accounting/income-statement", response_model=IncomeStatementAnalysisResponse)
def accounting_income_statement(req: DREFieldsRequest) -> IncomeStatementAnalysisResponse:
    """Analisa uma DRE: subtotais (lucro bruto/operacional/líquido, EBITDA) e
    análise vertical (cada conta como % da receita líquida)."""
    dre = DRE(**req.model_dump())
    vertical = analise_vertical(
        {
            "custo_produtos_vendidos": dre.custo_produtos_vendidos,
            "despesas_operacionais": dre.despesas_operacionais,
            "lucro_liquido": dre.lucro_liquido,
        },
        base=dre.receita_liquida,
    )
    return IncomeStatementAnalysisResponse(
        receita_liquida=dre.receita_liquida,
        lucro_bruto=dre.lucro_bruto,
        lucro_operacional=dre.lucro_operacional,
        lucro_antes_ir_csll=dre.lucro_antes_ir_csll,
        lucro_liquido=dre.lucro_liquido,
        ebitda=dre.ebitda,
        analise_vertical=vertical,
    )


@app.post("/accounting/cash-flow", response_model=DFCResponse)
def accounting_cash_flow(req: DFCRequest) -> DFCResponse:
    """Calcula a variação de caixa e o caixa final a partir dos três fluxos
    da DFC (CPC 03 (R2)): operacional, investimento e financiamento."""
    dfc = DFC(**req.model_dump())
    return DFCResponse(
        fluxo_operacional=dfc.fluxo_operacional,
        fluxo_investimento=dfc.fluxo_investimento,
        fluxo_financiamento=dfc.fluxo_financiamento,
        variacao_caixa=dfc.variacao_caixa,
        caixa_inicial=dfc.caixa_inicial,
        caixa_final=dfc.caixa_final,
    )


@app.post("/accounting/financial-indicators", response_model=FinancialIndicatorsResponse)
def accounting_financial_indicators(
    balanco: BalancoPatrimonialRequest, dre: DREFieldsRequest
) -> FinancialIndicatorsResponse:
    """Indicadores que combinam Balanço e DRE (rentabilidade exige os dois:
    ex. ROE = lucro líquido da DRE / patrimônio líquido do Balanço)."""
    try:
        bp = BalancoPatrimonial(**balanco.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_clean_validation_message(exc)) from exc

    dre_model = DRE(**dre.model_dump())
    liquidez = indicadores_liquidez(bp)
    endividamento = indicadores_endividamento(bp)
    rentabilidade = indicadores_rentabilidade(dre_model, bp)

    return FinancialIndicatorsResponse(
        liquidez_corrente=liquidez.liquidez_corrente,
        liquidez_seca=liquidez.liquidez_seca,
        liquidez_geral=liquidez.liquidez_geral,
        liquidez_imediata=liquidez.liquidez_imediata,
        endividamento_geral=endividamento.endividamento_geral,
        composicao_endividamento=endividamento.composicao_endividamento,
        imobilizacao_patrimonio_liquido=endividamento.imobilizacao_patrimonio_liquido,
        margem_bruta=rentabilidade.margem_bruta,
        margem_operacional=rentabilidade.margem_operacional,
        margem_liquida=rentabilidade.margem_liquida,
        margem_ebitda=rentabilidade.margem_ebitda,
        roe=rentabilidade.roe,
        roa=rentabilidade.roa,
        ebitda=rentabilidade.ebitda,
    )


@app.post("/accounting/horizontal-analysis", response_model=dict[str, float | None])
def accounting_horizontal_analysis(req: HorizontalAnalysisRequest) -> dict[str, float | None]:
    """Análise horizontal genérica: variação percentual de cada conta entre
    dois períodos. Funciona tanto para contas do Balanço quanto da DRE —
    basta informar os mesmos nomes de conta nos dois dicionários."""
    return analise_horizontal(req.valores_periodo_atual, req.valores_periodo_anterior)


@app.post("/documents/upload", response_model=DocumentResponse)
async def documents_upload(file: UploadFile) -> DocumentResponse:
    """Recebe um arquivo (PDF, DOCX, XLSX, CSV, XML ou TXT), extrai o texto e
    persiste em disco (ver documents/storage.py — sem banco de dados ainda).
    Não roda a análise por IA aqui; isso é um passo separado (POST
    /documents/{id}/analyze), já que depende do Ollama e pode ser lento."""
    if not file.filename:
        raise HTTPException(status_code=422, detail="Nome do arquivo ausente.")

    formato = formato_por_extensao(file.filename)
    if formato not in FORMATOS_SUPORTADOS:
        raise HTTPException(
            status_code=415,
            detail=f"Formato '.{formato}' não suportado. Use: {', '.join(sorted(FORMATOS_SUPORTADOS))}.",
        )

    content = await file.read()
    if len(content) > settings.documents_max_size_bytes:
        max_mb = settings.documents_max_size_bytes / (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Arquivo maior que o limite de {max_mb:.0f} MB.")

    record = documents_storage.save_upload(file.filename, content)
    return _to_document_response(record)


@app.get("/documents", response_model=list[DocumentResponse])
def documents_list() -> list[DocumentResponse]:
    return [_to_document_response(r) for r in documents_storage.list_documents()]


@app.get("/documents/{doc_id}", response_model=DocumentResponse)
def documents_get(doc_id: str) -> DocumentResponse:
    record = documents_storage.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return _to_document_response(record)


@app.get("/documents/{doc_id}/text", response_model=DocumentTextResponse)
def documents_get_text(doc_id: str) -> DocumentTextResponse:
    record = documents_storage.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    text = documents_storage.get_document_text(doc_id) or ""
    return DocumentTextResponse(id=doc_id, text=text)


@app.post("/documents/{doc_id}/analyze", response_model=DocumentAnalysisResponse)
def documents_analyze(doc_id: str) -> DocumentAnalysisResponse:
    """Roda a análise por IA (Ollama) sobre o texto já extraído do
    documento. Se o Ollama não estiver instalado/rodando, retorna o
    documento com `analysis_error` preenchido em vez de falhar com 500 —
    mesmo padrão usado no chat (app/chat_service.py)."""
    record = documents_storage.get_document(doc_id)
    if not record:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    if record.status != "processado":
        raise HTTPException(
            status_code=422, detail="Documento não foi processado com sucesso, não é possível analisar."
        )

    text = documents_storage.get_document_text(doc_id) or ""
    try:
        analysis = analyze_document_text(text, record.filename)
        updated = documents_storage.update_analysis(doc_id, analysis, None)
    except RuntimeError as exc:
        updated = documents_storage.update_analysis(doc_id, None, str(exc))

    return DocumentAnalysisResponse(
        id=doc_id, analysis=updated.analysis, analysis_error=updated.analysis_error
    )


@app.delete("/documents/{doc_id}")
def documents_delete(doc_id: str) -> dict:
    deleted = documents_storage.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> ChatResponse:
    result = answer_question(req.question, top_k=req.top_k)
    return ChatResponse(
        answer=result.answer,
        sources=result.sources,
        reference_date=result.reference_date,
        context_found=result.context_found,
    )


@app.get("/chat/stream")
def chat_stream_endpoint(question: str, top_k: int | None = None) -> StreamingResponse:
    """Versão em streaming (Server-Sent Events) de /chat, para uso com
    EventSource no frontend. Ver app/chat_service.py::stream_answer_question
    para o protocolo de eventos (sources/token/done/error)."""
    return StreamingResponse(
        stream_answer_question(question, top_k=top_k),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
