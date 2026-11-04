"""Cálculo de IRPJ, CSLL, PIS e COFINS no regime de Lucro Presumido.

Não inclui ISS (municipal) nem ICMS (estadual): suas alíquotas variam por
município/estado e produto/serviço e precisam ser informadas separadamente.

Desde 2026, os percentuais de presunção têm acréscimo de 10% sobre a parcela
da receita bruta que excede um limite proporcional trimestral de
R$ 1.250.000,00 (1/4 do limite anual de R$ 5.000.000,00), com o saldo não
utilizado de um trimestre se somando ao limite dos trimestres seguintes do
mesmo ano-calendário (IN RFB nº 2305/2025, art. 15, §§1º-4º, com a redação
da IN RFB nº 2306/2026).

NÃO implementado: a reconciliação do último trimestre do ano (art. 15,
§§5º-8º), que pode recalcular trimestres anteriores com alocação
proporcional entre os que excederam o limite, e eventualmente gerar
restituição. Esta função cobre apenas o cálculo provisório trimestre a
trimestre (válido integralmente para o 1º-3º trimestre).
"""
from dataclasses import dataclass

from taxation.rates import (
    CSLL_ALIQUOTA_GERAL,
    IRPJ_ADICIONAL_ALIQUOTA,
    IRPJ_ADICIONAL_LIMITE_TRIMESTRAL,
    IRPJ_ALIQUOTA_BASE,
    LUCRO_PRESUMIDO_MAJORACAO,
    LUCRO_PRESUMIDO_PERCENTUAIS,
    PIS_COFINS_CUMULATIVO,
)

ATIVIDADES_VALIDAS = tuple(LUCRO_PRESUMIDO_PERCENTUAIS.dados.keys())


@dataclass
class ResultadoLucroPresumido:
    atividade: str
    receita_trimestre: float
    parcela_receita_majorada: float
    saldo_limite_nao_utilizado: float  # a repassar como entrada do próximo trimestre
    base_presumida_irpj: float
    base_presumida_csll: float
    irpj: float
    irpj_adicional: float
    csll: float
    pis: float
    cofins: float
    total_tributos: float
    carga_tributaria_efetiva: float
    fonte: str


def _parcelas_normal_e_majorada(
    receita_trimestre: float, saldo_limite_nao_utilizado_anterior: float
) -> tuple[float, float, float]:
    """Retorna (parcela_normal, parcela_majorada, novo_saldo_nao_utilizado),
    aplicando o limite proporcional trimestral com carryforward (IN RFB
    2305/2025, art. 15, §§1º-4º)."""
    limite_base = LUCRO_PRESUMIDO_MAJORACAO.dados["limite_proporcional_trimestral"]
    limite_disponivel = limite_base + saldo_limite_nao_utilizado_anterior

    if receita_trimestre <= limite_disponivel:
        return receita_trimestre, 0.0, limite_disponivel - receita_trimestre
    return limite_disponivel, receita_trimestre - limite_disponivel, 0.0


def calcular_lucro_presumido(
    receita_trimestre: float,
    atividade: str,
    saldo_limite_nao_utilizado_anterior: float = 0.0,
) -> ResultadoLucroPresumido:
    if atividade not in ATIVIDADES_VALIDAS:
        raise ValueError(f"Atividade inválida: {atividade}. Use uma de {ATIVIDADES_VALIDAS}")

    percentuais = LUCRO_PRESUMIDO_PERCENTUAIS.dados[atividade]
    acrescimo = LUCRO_PRESUMIDO_MAJORACAO.dados["acrescimo_percentual"]

    parcela_normal, parcela_majorada, novo_saldo = _parcelas_normal_e_majorada(
        receita_trimestre, saldo_limite_nao_utilizado_anterior
    )

    base_irpj = (
        parcela_normal * percentuais["irpj"]
        + parcela_majorada * percentuais["irpj"] * (1 + acrescimo)
    )
    base_csll = (
        parcela_normal * percentuais["csll"]
        + parcela_majorada * percentuais["csll"] * (1 + acrescimo)
    )

    irpj = base_irpj * IRPJ_ALIQUOTA_BASE
    excedente = max(0.0, base_irpj - IRPJ_ADICIONAL_LIMITE_TRIMESTRAL)
    irpj_adicional = excedente * IRPJ_ADICIONAL_ALIQUOTA
    csll = base_csll * CSLL_ALIQUOTA_GERAL

    pis = receita_trimestre * PIS_COFINS_CUMULATIVO["pis"]
    cofins = receita_trimestre * PIS_COFINS_CUMULATIVO["cofins"]

    total = irpj + irpj_adicional + csll + pis + cofins

    return ResultadoLucroPresumido(
        atividade=atividade,
        receita_trimestre=receita_trimestre,
        parcela_receita_majorada=parcela_majorada,
        saldo_limite_nao_utilizado=novo_saldo,
        base_presumida_irpj=base_irpj,
        base_presumida_csll=base_csll,
        irpj=irpj,
        irpj_adicional=irpj_adicional,
        csll=csll,
        pis=pis,
        cofins=cofins,
        total_tributos=total,
        carga_tributaria_efetiva=total / receita_trimestre if receita_trimestre else 0.0,
        fonte=f"{LUCRO_PRESUMIDO_PERCENTUAIS.fonte}; {LUCRO_PRESUMIDO_MAJORACAO.fonte}",
    )
