"""Compara a carga tributária estimada entre Simples Nacional, Lucro
Presumido e Lucro Real para o mesmo período, dado um perfil de empresa.

Comparação é aproximada: Lucro Real exige o lucro real trimestral (que o
usuário precisa informar ou estimar), e nenhum dos três inclui ISS/ICMS.
"""
from dataclasses import dataclass

from taxation.lucro_presumido import calcular_lucro_presumido
from taxation.lucro_real import calcular_lucro_real
from taxation.simples_nacional import calcular_das


@dataclass
class ComparacaoRegimes:
    receita_trimestre: float
    simples_nacional: dict | None
    lucro_presumido: dict
    lucro_real: dict
    regime_mais_vantajoso: str
    aviso: str


def comparar_regimes(
    receita_trimestre: float,
    rbt12: float,
    anexo_simples: str | None,
    atividade_lucro_presumido: str,
    lucro_real_trimestre: float,
    elegivel_simples: bool = True,
    saldo_limite_nao_utilizado_anterior: float = 0.0,
) -> ComparacaoRegimes:
    resultados: dict[str, float] = {}

    simples_resultado = None
    if elegivel_simples and anexo_simples:
        das = calcular_das(receita_trimestre, rbt12, anexo_simples)
        simples_resultado = das.__dict__
        resultados["simples_nacional"] = das.valor_das

    presumido = calcular_lucro_presumido(
        receita_trimestre, atividade_lucro_presumido, saldo_limite_nao_utilizado_anterior
    )
    resultados["lucro_presumido"] = presumido.total_tributos

    real = calcular_lucro_real(lucro_real_trimestre, receita_trimestre)
    resultados["lucro_real"] = real.total_tributos

    mais_vantajoso = min(resultados, key=resultados.get)

    return ComparacaoRegimes(
        receita_trimestre=receita_trimestre,
        simples_nacional=simples_resultado,
        lucro_presumido=presumido.__dict__,
        lucro_real=real.__dict__,
        regime_mais_vantajoso=mais_vantajoso,
        aviso=(
            "Comparação não inclui ISS/ICMS (variam por município/estado e "
            "atividade) nem particularidades do LALUR no Lucro Real. Use como "
            "estimativa inicial, não como decisão final de regime tributário."
        ),
    )
