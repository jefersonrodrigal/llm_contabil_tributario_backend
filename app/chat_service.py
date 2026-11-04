"""Camada que liga recuperação (RAG) + geração (Ollama), aplicando as regras
de confiabilidade exigidas para o domínio contábil/tributário:
não inventar artigos/alíquotas/pronunciamentos, não apresentar norma
revogada como vigente, sempre citar fontes e data de referência, e declarar
quando não há evidência suficiente.
"""
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from ai_engine.client import RetrievedChunk, chat, hybrid_search, stream_chat

SYSTEM_PROMPT = """Você é um assistente especializado em Ciências Contábeis, \
Contabilidade Brasileira, Legislação Tributária e Reforma Tributária do Brasil.

Regras obrigatórias:
1. Responda SOMENTE com base nos trechos de contexto fornecidos abaixo. \
Nunca invente artigos de lei, alíquotas, pronunciamentos contábeis ou normas que \
não estejam no contexto.
2. Se o contexto não tiver informação suficiente para responder com segurança, \
diga explicitamente que não possui informações suficientes — não tente adivinhar.
3. Sempre indique, ao final da resposta, as fontes utilizadas (norma, número, \
artigo quando houver) e a data de referência informada abaixo.
4. Diferencie claramente o que é texto da legislação/norma, o que é interpretação \
técnica sua, e deixe claro quando não há consenso ou a questão exige análise \
individualizada por um profissional contábil/tributário habilitado.
5. Nunca apresente uma norma marcada como revogada no contexto como se estivesse vigente.

Data de referência desta resposta: {data_referencia}
"""


@dataclass
class ChatResult:
    answer: str
    sources: list[dict]
    reference_date: str
    context_found: bool


def _format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.metadata
        loc = f"Art. {meta.get('artigo')}" if meta.get("artigo") else ""
        header = f"[{i}] {meta.get('titulo')} ({meta.get('tipo_norma')}) {loc} — status: {meta.get('status')}"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n".join(blocks)


def _format_sources(chunks: list[RetrievedChunk]) -> list[dict]:
    seen = set()
    sources = []
    for chunk in chunks:
        meta = chunk.metadata
        key = (meta.get("fonte_id"), meta.get("artigo"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "titulo": meta.get("titulo"),
                "tipo_norma": meta.get("tipo_norma"),
                "numero": meta.get("numero"),
                "artigo": meta.get("artigo") or None,
                "status": meta.get("status"),
                "url_fonte": meta.get("url_fonte"),
            }
        )
    return sources


def _build_messages(question: str, chunks: list[RetrievedChunk], reference_date: str) -> list[dict]:
    context = _format_context(chunks)
    system = SYSTEM_PROMPT.format(data_referencia=reference_date)
    user = f"Contexto recuperado da base documental:\n\n{context}\n\nPergunta do usuário: {question}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def answer_question(question: str, top_k: int | None = None) -> ChatResult:
    chunks = hybrid_search(question, top_k=top_k)
    reference_date = date.today().isoformat()

    if not chunks:
        return ChatResult(
            answer=(
                "Não há documentos indexados na base de conhecimento ainda, ou nenhum "
                "trecho relevante foi encontrado para esta pergunta. Não possuo "
                "informações suficientes para responder com segurança."
            ),
            sources=[],
            reference_date=reference_date,
            context_found=False,
        )

    messages = _build_messages(question, chunks, reference_date)
    answer = chat(messages)

    return ChatResult(
        answer=answer,
        sources=_format_sources(chunks),
        reference_date=reference_date,
        context_found=True,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_answer_question(question: str, top_k: int | None = None) -> Iterator[str]:
    """Mesma lógica de `answer_question`, mas produzindo eventos SSE:
    - 'sources': fontes recuperadas + data de referência (enviado antes de
      qualquer geração, para a UI já poder exibi-las).
    - 'token': fragmento de texto da resposta, conforme o Ollama o produz.
    - 'done': geração concluída.
    - 'stream_error': falha ao contatar o Ollama (ex.: não instalado/rodando).
      Usa um nome diferente de 'error' de propósito: EventSource do browser
      trata qualquer SSE 'event: error' como seu evento nativo de falha de
      conexão, tornando impossível diferenciar um erro da aplicação de uma
      queda de conexão real se usássemos o mesmo nome.
    """
    chunks = hybrid_search(question, top_k=top_k)
    reference_date = date.today().isoformat()

    if not chunks:
        yield _sse(
            "sources",
            {"sources": [], "reference_date": reference_date, "context_found": False},
        )
        fallback = (
            "Não há documentos indexados na base de conhecimento ainda, ou nenhum "
            "trecho relevante foi encontrado para esta pergunta. Não possuo "
            "informações suficientes para responder com segurança."
        )
        yield _sse("token", {"delta": fallback})
        yield _sse("done", {})
        return

    yield _sse(
        "sources",
        {
            "sources": _format_sources(chunks),
            "reference_date": reference_date,
            "context_found": True,
        },
    )

    messages = _build_messages(question, chunks, reference_date)
    try:
        for delta in stream_chat(messages):
            yield _sse("token", {"delta": delta})
    except RuntimeError as exc:
        yield _sse("stream_error", {"message": str(exc)})
        return
    yield _sse("done", {})
