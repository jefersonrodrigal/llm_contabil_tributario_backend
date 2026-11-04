"""Simulação de IBS/CBS durante a fase de testes de 2026 da Reforma Tributária.

Cobre apenas o período vigente verificado (2026, alíquotas-teste da LC
214/2025). O cronograma de 2027 em diante (redução de PIS/COFINS/ICMS/ISS,
alíquota de referência fixada pelo Senado etc.) depende de regulamentação
ainda não totalmente verificada nesta base — `proximos_marcos()` apenas lista
o que é publicamente conhecido, sem tratar como definitivo.
"""
from dataclasses import dataclass

from taxation.rates import REFORMA_TRIBUTARIA_FASE_TESTE_2026


@dataclass
class ResultadoIBSCBS:
    valor_operacao: float
    cbs: float
    ibs_estadual: float
    ibs_municipal: float
    total_ibs_cbs: float
    aplica_simples_nacional: bool
    observacao: str
    fonte: str


def simular_ibs_cbs_teste_2026(valor_operacao: float, optante_simples: bool = False) -> ResultadoIBSCBS:
    dados = REFORMA_TRIBUTARIA_FASE_TESTE_2026.dados

    if optante_simples and not dados["aplica_simples_nacional"]:
        return ResultadoIBSCBS(
            valor_operacao=valor_operacao,
            cbs=0.0,
            ibs_estadual=0.0,
            ibs_municipal=0.0,
            total_ibs_cbs=0.0,
            aplica_simples_nacional=False,
            observacao="Optantes do Simples Nacional não se sujeitam à alíquota-teste de 2026.",
            fonte=REFORMA_TRIBUTARIA_FASE_TESTE_2026.fonte,
        )

    cbs = valor_operacao * dados["cbs_aliquota"]
    ibs_estadual = valor_operacao * dados["ibs_aliquota_estadual"]
    ibs_municipal = valor_operacao * dados["ibs_aliquota_municipal"]

    return ResultadoIBSCBS(
        valor_operacao=valor_operacao,
        cbs=cbs,
        ibs_estadual=ibs_estadual,
        ibs_municipal=ibs_municipal,
        total_ibs_cbs=cbs + ibs_estadual + ibs_municipal,
        aplica_simples_nacional=dados["aplica_simples_nacional"],
        observacao=dados["observacao"],
        fonte=REFORMA_TRIBUTARIA_FASE_TESTE_2026.fonte,
    )


def proximos_marcos() -> list[dict]:
    """Marcos do cronograma de transição citados publicamente. Cada entrada
    traz o status 'a_confirmar' quando a regra ainda depende de
    regulamentação adicional — não deve ser apresentada como vigente sem
    nova verificação na fonte."""
    return [
        {
            "periodo": "2026",
            "descricao": "Fase de testes: CBS 0,9% + IBS estadual 0,1% (municipal 0%), sem carga adicional.",
            "status": "vigente",
            "fonte": "LC 214/2025, arts. 343 e 346",
        },
        {
            "periodo": "2027-2028",
            "descricao": (
                "Mencionado publicamente: CBS cobrada por alíquota fixada pela União "
                "menos 0,1 p.p.; IBS passa a 0,05% estadual + 0,05% municipal; "
                "extinção de PIS/COFINS."
            ),
            "status": "a_confirmar",
            "fonte": "Análises de mercado sobre a LC 214/2025 — confirmar na norma antes de aplicar.",
        },
        {
            "periodo": "2029-2032",
            "descricao": "Redução progressiva de ICMS/ISS com aumento proporcional de IBS/CBS.",
            "status": "a_confirmar",
            "fonte": "EC 132/2023 — cronograma geral; detalhamento depende de regulamentação adicional.",
        },
        {
            "periodo": "2033",
            "descricao": "Extinção de ICMS e ISS; sistema IBS/CBS plenamente vigente.",
            "status": "a_confirmar",
            "fonte": "EC 132/2023, art. 125/ADCT — confirmar redação vigente antes de aplicar.",
        },
    ]
