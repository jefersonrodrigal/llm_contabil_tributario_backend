"""Cálculo do DAS (Simples Nacional) por faixa de RBT12, com apoio ao
enquadramento no Fator R (Anexo III x Anexo V) para prestadores de serviço.
"""
from dataclasses import dataclass

from taxation.rates import (
    SIMPLES_NACIONAL_ANEXOS,
    SIMPLES_NACIONAL_FATOR_R_CORTE,
    SIMPLES_NACIONAL_LIMITE_RBT12,
    Faixa,
)

ANEXOS_VALIDOS = tuple(SIMPLES_NACIONAL_ANEXOS.dados.keys())


@dataclass
class ResultadoDAS:
    anexo: str
    rbt12: float
    receita_mes: float
    faixa_indice: int
    aliquota_nominal: float
    aliquota_efetiva: float
    valor_das: float
    fonte: str
    vigencia_inicio: str


_LIMITES_FAIXA = [180_000.0, 360_000.0, 720_000.0, 1_800_000.0, 3_600_000.0, 4_800_000.0]


def determinar_anexo_servicos(folha_12_meses: float, rbt12: float) -> str:
    """Fator R: folha de pagamento (c/ encargos e pró-labore) / RBT12.

    >= 28% -> Anexo III (CPP incluída no DAS, geralmente mais vantajoso).
    < 28%  -> Anexo V.
    """
    if rbt12 <= 0:
        raise ValueError("RBT12 deve ser positivo para calcular o Fator R")
    fator_r = folha_12_meses / rbt12
    return "III" if fator_r >= SIMPLES_NACIONAL_FATOR_R_CORTE else "V"


def calcular_das(receita_mes: float, rbt12: float, anexo: str) -> ResultadoDAS:
    if anexo not in ANEXOS_VALIDOS:
        raise ValueError(f"Anexo inválido: {anexo}. Use um de {ANEXOS_VALIDOS}")
    if rbt12 > SIMPLES_NACIONAL_LIMITE_RBT12:
        raise ValueError(
            f"RBT12 de R$ {rbt12:,.2f} excede o limite do Simples Nacional "
            f"(R$ {SIMPLES_NACIONAL_LIMITE_RBT12:,.2f}); empresa não é elegível."
        )

    faixas = SIMPLES_NACIONAL_ANEXOS.dados[anexo]
    idx = next(i for i, limite in enumerate(_LIMITES_FAIXA) if rbt12 <= limite)
    faixa = faixas[idx]

    aliquota_efetiva = (rbt12 * faixa.aliquota_nominal - faixa.parcela_deduzir) / rbt12
    valor_das = receita_mes * aliquota_efetiva

    return ResultadoDAS(
        anexo=anexo,
        rbt12=rbt12,
        receita_mes=receita_mes,
        faixa_indice=idx + 1,
        aliquota_nominal=faixa.aliquota_nominal,
        aliquota_efetiva=aliquota_efetiva,
        valor_das=valor_das,
        fonte=SIMPLES_NACIONAL_ANEXOS.fonte,
        vigencia_inicio=SIMPLES_NACIONAL_ANEXOS.vigencia_inicio.isoformat(),
    )
