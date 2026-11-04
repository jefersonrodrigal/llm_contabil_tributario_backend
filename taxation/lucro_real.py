"""Cálculo de IRPJ, CSLL, PIS e COFINS no regime de Lucro Real.

Versão simplificada: parte do lucro líquido contábil já ajustado (lucro real
informado pelo usuário, após adições/exclusões da apuração). Não refaz a
apuração completa do LALUR. PIS/COFINS não-cumulativos são calculados sobre a
receita bruta menos créditos informados pelo usuário (não calcula créditos
automaticamente — isso depende de notas fiscais/insumos reais da empresa).

Não inclui ISS (municipal) nem ICMS (estadual).
"""
from dataclasses import dataclass

from taxation.rates import (
    CSLL_ALIQUOTA_GERAL,
    IRPJ_ADICIONAL_ALIQUOTA,
    IRPJ_ADICIONAL_LIMITE_TRIMESTRAL,
    IRPJ_ALIQUOTA_BASE,
    PIS_COFINS_NAO_CUMULATIVO,
)


@dataclass
class ResultadoLucroReal:
    lucro_real_trimestre: float
    receita_bruta_trimestre: float
    creditos_pis_cofins: float
    irpj: float
    irpj_adicional: float
    csll: float
    pis: float
    cofins: float
    total_tributos: float
    carga_tributaria_efetiva: float


def calcular_lucro_real(
    lucro_real_trimestre: float,
    receita_bruta_trimestre: float,
    creditos_pis_cofins: float = 0.0,
) -> ResultadoLucroReal:
    if lucro_real_trimestre < 0:
        # Prejuízo fiscal: sem IRPJ/CSLL devidos no período (compensação de
        # prejuízos em períodos futuros não é tratada aqui).
        irpj = irpj_adicional = csll = 0.0
    else:
        irpj = lucro_real_trimestre * IRPJ_ALIQUOTA_BASE
        excedente = max(0.0, lucro_real_trimestre - IRPJ_ADICIONAL_LIMITE_TRIMESTRAL)
        irpj_adicional = excedente * IRPJ_ADICIONAL_ALIQUOTA
        csll = lucro_real_trimestre * CSLL_ALIQUOTA_GERAL

    base_pis_cofins = max(0.0, receita_bruta_trimestre - creditos_pis_cofins)
    pis = base_pis_cofins * PIS_COFINS_NAO_CUMULATIVO["pis"]
    cofins = base_pis_cofins * PIS_COFINS_NAO_CUMULATIVO["cofins"]

    total = irpj + irpj_adicional + csll + pis + cofins

    return ResultadoLucroReal(
        lucro_real_trimestre=lucro_real_trimestre,
        receita_bruta_trimestre=receita_bruta_trimestre,
        creditos_pis_cofins=creditos_pis_cofins,
        irpj=irpj,
        irpj_adicional=irpj_adicional,
        csll=csll,
        pis=pis,
        cofins=cofins,
        total_tributos=total,
        carga_tributaria_efetiva=(
            total / receita_bruta_trimestre if receita_bruta_trimestre else 0.0
        ),
    )
