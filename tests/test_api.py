import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["chunks_indexados"], int)


def test_legislation_sources_endpoint_matches_manifest():
    resp = client.get("/legislation/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 26
    first = data[0]
    assert {"fonte_id", "titulo", "tipo_norma", "status", "url_fonte"} <= first.keys()


def test_taxation_reform_timeline_endpoint():
    resp = client.get("/taxation/reform-timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    assert data[0]["periodo"] == "2026"
    assert data[0]["status"] == "vigente"


def test_taxation_ibs_cbs_simulacao_regime_normal():
    resp = client.post(
        "/taxation/ibs-cbs-simulacao", json={"valor_operacao": 10_000, "optante_simples": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cbs"] == 90.0
    assert data["ibs_estadual"] == 10.0
    assert data["total_ibs_cbs"] == 100.0


def test_taxation_ibs_cbs_simulacao_simples_nacional():
    resp = client.post(
        "/taxation/ibs-cbs-simulacao", json={"valor_operacao": 10_000, "optante_simples": True}
    )
    assert resp.status_code == 200
    assert resp.json()["total_ibs_cbs"] == 0.0


def test_taxation_ibs_cbs_simulacao_rejeita_valor_negativo():
    resp = client.post("/taxation/ibs-cbs-simulacao", json={"valor_operacao": -100})
    assert resp.status_code == 422


def test_legislation_source_content_retorna_chunks_em_ordem():
    resp = client.get("/legislation/sources/lc214_2025/content")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fonte_id"] == "lc214_2025"
    assert data["total_chunks"] == len(data["chunks"])
    assert data["total_chunks"] > 0
    indices = [c["chunk_index"] for c in data["chunks"]]
    assert indices == sorted(indices)


def test_legislation_source_content_404_para_fonte_inexistente():
    resp = client.get("/legislation/sources/fonte-que-nao-existe/content")
    assert resp.status_code == 404


_BP_EXEMPLO = {
    "ativo_circulante": 200_000,
    "ativo_realizavel_longo_prazo": 20_000,
    "ativo_imobilizado": 150_000,
    "ativo_intangivel": 10_000,
    "ativo_investimentos": 20_000,
    "passivo_circulante": 100_000,
    "passivo_nao_circulante": 80_000,
    "patrimonio_liquido": 220_000,
    "estoques": 50_000,
    "disponivel": 30_000,
}

_DRE_EXEMPLO = {
    "receita_bruta": 500_000,
    "deducoes_receita": 50_000,
    "custo_produtos_vendidos": 200_000,
    "despesas_operacionais": 100_000,
    "resultado_financeiro": -5_000,
    "depreciacao_amortizacao": 20_000,
    "irpj_csll": 30_000,
}


def test_accounting_balance_sheet_endpoint():
    resp = client.post("/accounting/balance-sheet", json=_BP_EXEMPLO)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ativo_total"] == pytest.approx(400_000)
    assert data["liquidez_corrente"] == pytest.approx(2.0)
    assert data["analise_vertical"]["ativo_circulante"] == pytest.approx(0.5)


def test_accounting_balance_sheet_endpoint_rejeita_balanco_que_nao_fecha():
    bp_quebrado = {**_BP_EXEMPLO, "patrimonio_liquido": 1_000}
    resp = client.post("/accounting/balance-sheet", json=bp_quebrado)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "Balanço não fecha" in detail
    # Não deve vazar o dump técnico do pydantic (type=value_error, input_value=...)
    assert "input_value" not in detail


def test_accounting_income_statement_endpoint():
    resp = client.post("/accounting/income-statement", json=_DRE_EXEMPLO)
    assert resp.status_code == 200
    data = resp.json()
    assert data["receita_liquida"] == pytest.approx(450_000)
    assert data["ebitda"] == pytest.approx(170_000)


def test_accounting_cash_flow_endpoint():
    resp = client.post(
        "/accounting/cash-flow",
        json={
            "fluxo_operacional": 100_000,
            "fluxo_investimento": -40_000,
            "fluxo_financiamento": -10_000,
            "caixa_inicial": 20_000,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["variacao_caixa"] == pytest.approx(50_000)
    assert data["caixa_final"] == pytest.approx(70_000)


def test_accounting_financial_indicators_endpoint():
    resp = client.post(
        "/accounting/financial-indicators",
        json={"balanco": _BP_EXEMPLO, "dre": _DRE_EXEMPLO},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["margem_bruta"] == pytest.approx(250_000 / 450_000)
    assert data["roe"] is not None


def test_accounting_horizontal_analysis_endpoint():
    resp = client.post(
        "/accounting/horizontal-analysis",
        json={
            "valores_periodo_atual": {"receita": 550_000},
            "valores_periodo_anterior": {"receita": 500_000},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["receita"] == pytest.approx(0.10)


@pytest.fixture
def isolated_documents_storage(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "documents_storage_dir", tmp_path / "documents")
    yield


def test_documents_upload_and_list(isolated_documents_storage):
    resp = client.post(
        "/documents/upload",
        files={"file": ("nota.txt", b"Nota fiscal de servico, valor R$ 1.000,00.", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processado"
    assert data["filename"] == "nota.txt"
    doc_id = data["id"]

    listed = client.get("/documents")
    assert listed.status_code == 200
    assert any(d["id"] == doc_id for d in listed.json())

    fetched = client.get(f"/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "nota.txt"

    text_resp = client.get(f"/documents/{doc_id}/text")
    assert text_resp.status_code == 200
    assert "Nota fiscal" in text_resp.json()["text"]


def test_documents_upload_rejeita_formato_nao_suportado(isolated_documents_storage):
    resp = client.post(
        "/documents/upload",
        files={"file": ("virus.exe", b"conteudo", "application/octet-stream")},
    )
    assert resp.status_code == 415


def test_documents_delete(isolated_documents_storage):
    upload = client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"conteudo qualquer", "text/plain")},
    )
    doc_id = upload.json()["id"]

    deleted = client.delete(f"/documents/{doc_id}")
    assert deleted.status_code == 200

    missing = client.get(f"/documents/{doc_id}")
    assert missing.status_code == 404


def test_cors_preflight_permite_delete_em_documents():
    # Regressão: TestClient.delete(...) não passa pelo bloqueio de CORS do
    # navegador (só é enforced client-side), então um teste chamando DELETE
    # direto não pegaria o middleware esquecendo de liberar o método — só o
    # preflight OPTIONS simulado abaixo reproduz o que o navegador faz.
    resp = client.options(
        "/documents/00000000-0000-0000-0000-000000000000",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    assert resp.status_code == 200
    allowed = resp.headers.get("access-control-allow-methods", "")
    assert "DELETE" in allowed


def test_documents_analyze_sem_ollama_retorna_erro_tratavel(isolated_documents_storage, monkeypatch):
    # Simula o Ollama fora do ar (independente de estar instalado nesta
    # máquina): a análise deve falhar de forma tratável (não derrubar o
    # endpoint com 500).
    def _unavailable(messages, temperature=0.2):
        raise RuntimeError("Não foi possível conectar ao Ollama em http://localhost:11434.")

    monkeypatch.setattr("documents.analysis.chat", _unavailable)

    upload = client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"Contrato de prestacao de servicos contabeis.", "text/plain")},
    )
    doc_id = upload.json()["id"]

    resp = client.post(f"/documents/{doc_id}/analyze")
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_error"] is not None
    assert "Ollama" in data["analysis_error"]
