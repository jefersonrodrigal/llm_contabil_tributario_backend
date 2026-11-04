"""Indicadores financeiros clássicos de análise das demonstrações contábeis:
liquidez, endividamento, rentabilidade/margens, e análise vertical/horizontal.
"""
from dataclasses import dataclass

from accounting.balance_sheet import BalancoPatrimonial
from accounting.income_statement import DRE


def _safe_div(numerador: float, denominador: float) -> float | None:
    return numerador / denominador if denominador else None


@dataclass
class IndicadoresLiquidez:
    liquidez_corrente: float | None
    liquidez_seca: float | None
    liquidez_geral: float | None
    liquidez_imediata: float | None


def indicadores_liquidez(bp: BalancoPatrimonial) -> IndicadoresLiquidez:
    return IndicadoresLiquidez(
        liquidez_corrente=_safe_div(bp.ativo_circulante, bp.passivo_circulante),
        liquidez_seca=_safe_div(bp.ativo_circulante - bp.estoques, bp.passivo_circulante),
        liquidez_geral=_safe_div(
            bp.ativo_circulante + bp.ativo_realizavel_longo_prazo,
            bp.passivo_total_exigivel,
        ),
        liquidez_imediata=_safe_div(bp.disponivel, bp.passivo_circulante),
    )


@dataclass
class IndicadoresEndividamento:
    endividamento_geral: float | None  # (PC+PNC) / Ativo total
    composicao_endividamento: float | None  # PC / (PC+PNC)
    imobilizacao_patrimonio_liquido: float | None  # Ativo imobilizado / PL


def indicadores_endividamento(bp: BalancoPatrimonial) -> IndicadoresEndividamento:
    return IndicadoresEndividamento(
        endividamento_geral=_safe_div(bp.passivo_total_exigivel, bp.ativo_total),
        composicao_endividamento=_safe_div(bp.passivo_circulante, bp.passivo_total_exigivel),
        imobilizacao_patrimonio_liquido=_safe_div(bp.ativo_imobilizado, bp.patrimonio_liquido),
    )


@dataclass
class IndicadoresRentabilidade:
    margem_bruta: float | None
    margem_operacional: float | None
    margem_liquida: float | None
    roe: float | None  # retorno sobre o patrimônio líquido
    roa: float | None  # retorno sobre o ativo total
    ebitda: float
    margem_ebitda: float | None


def indicadores_rentabilidade(dre: DRE, bp: BalancoPatrimonial) -> IndicadoresRentabilidade:
    return IndicadoresRentabilidade(
        margem_bruta=_safe_div(dre.lucro_bruto, dre.receita_liquida),
        margem_operacional=_safe_div(dre.lucro_operacional, dre.receita_liquida),
        margem_liquida=_safe_div(dre.lucro_liquido, dre.receita_liquida),
        roe=_safe_div(dre.lucro_liquido, bp.patrimonio_liquido),
        roa=_safe_div(dre.lucro_liquido, bp.ativo_total),
        ebitda=dre.ebitda,
        margem_ebitda=_safe_div(dre.ebitda, dre.receita_liquida),
    )


def analise_vertical(valores: dict[str, float], base: float) -> dict[str, float | None]:
    """Cada conta como percentual de uma base (receita líquida na DRE, ativo
    total no Balanço)."""
    return {conta: _safe_div(valor, base) for conta, valor in valores.items()}


def analise_horizontal(
    valores_periodo_atual: dict[str, float], valores_periodo_base: dict[str, float]
) -> dict[str, float | None]:
    """Variação percentual de cada conta em relação ao período-base (ex.: ano anterior)."""
    variacoes = {}
    for conta, atual in valores_periodo_atual.items():
        base = valores_periodo_base.get(conta)
        if base is None:
            variacoes[conta] = None
            continue
        variacoes[conta] = _safe_div(atual - base, abs(base)) if base != 0 else None
    return variacoes
