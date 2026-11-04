"""Análise por IA de um documento já enviado e extraído (Fase 7).

Reaproveita o cliente do Ollama já usado pelo chat (via ai_engine.client) e
segue as mesmas regras de confiabilidade: analisar só o que está no
documento, sem inventar números/conclusões, e declarar quando o conteúdo
não parece ser contábil/tributário.
"""
from ai_engine.client import chat

MAX_CHARS_ENVIADOS = 12_000

SYSTEM_PROMPT = """Você é um assistente especializado em Ciências Contábeis e Legislação \
Tributária brasileira, analisando um documento enviado pelo usuário.

Regras obrigatórias:
1. Baseie-se SOMENTE no texto do documento fornecido abaixo. Não invente valores, \
cláusulas ou conclusões que não estejam no texto.
2. Resuma o tipo de documento e os pontos contábeis/tributários mais relevantes \
(valores, datas, partes envolvidas, obrigações, tributos citados), se houver.
3. Se o documento não tiver conteúdo contábil/tributário identificável, diga isso \
explicitamente em vez de forçar uma análise.
4. Seja objetivo — liste os pontos principais, não reproduza o documento inteiro.
"""


def analyze_document_text(text: str, filename: str) -> str:
    truncated = text[:MAX_CHARS_ENVIADOS]
    aviso_truncamento = (
        f"\n\n[Texto truncado em {MAX_CHARS_ENVIADOS} caracteres de um total de {len(text)}.]"
        if len(text) > MAX_CHARS_ENVIADOS
        else ""
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Documento: {filename}\n\n{truncated}{aviso_truncamento}",
        },
    ]
    return chat(messages)
