from app.chat_service import stream_answer_question


def test_stream_answer_question_sem_documentos(monkeypatch):
    monkeypatch.setattr("app.chat_service.hybrid_search", lambda question, top_k=None: [])

    events = list(stream_answer_question("pergunta sem contexto algum"))
    joined = "".join(events)

    assert "event: sources" in joined
    assert '"context_found": false' in joined
    assert "event: token" in joined
    assert "event: done" in joined
    assert "Não possuo" in joined


def test_stream_answer_question_erro_quando_ollama_indisponivel(monkeypatch):
    # Simula o Ollama fora do ar (independente de estar instalado nesta
    # máquina): uma pergunta com contexto real disponível deve emitir
    # 'sources' e depois 'stream_error' (não travar).
    def _unavailable(messages, temperature=0.2):
        raise RuntimeError("Não foi possível conectar ao Ollama em http://localhost:11434.")
        yield  # pragma: no cover - torna a função um gerador

    monkeypatch.setattr("app.chat_service.stream_chat", _unavailable)

    events = list(stream_answer_question("O que é o IBS?", top_k=2))
    joined = "".join(events)

    assert "event: sources" in joined
    assert "event: stream_error" in joined
    assert "Ollama" in joined
