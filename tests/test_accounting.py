import pytest

from accounting.balance_sheet import BalancoPatrimonial
from accounting.cash_flow import DFC
from accounting.financial_analysis import (
    analise_horizontal,
    analise_vertical,
    indicadores_endividamento,
    indicadores_liquidez,
    indicadores_rentabilidade,
)
from accounting.income_statement import DRE


def _bp_exemplo() -> BalancoPatrimonial:
    return BalancoPatrimonial(
        ativo_circulante=200_000,
        ativo_realizavel_longo_prazo=20_000,
        ativo_imobilizado=150_000,
        ativo_intangivel=10_000,
        ativo_investimentos=20_000,
        passivo_circulante=100_000,
        passivo_nao_circulante=80_000,
        patrimonio_liquido=220_000,
        estoques=50_000,
        disponivel=30_000,
    )


def test_balanco_patrimonial_fecha():
    bp = _bp_exemplo()
    assert bp.ativo_total == pytest.approx(400_000)
    assert bp.ativo_total == pytest.approx(bp.passivo_total_exigivel + bp.patrimonio_liquido)


def test_balanco_patrimonial_nao_fecha_levanta_erro():
    with pytest.raises(ValueError):
        BalancoPatrimonial(
            ativo_circulante=100_000,
            passivo_circulante=50_000,
            patrimonio_liquido=10_000,  # 100k != 50k + 10k
        )


def test_indicadores_liquidez():
    bp = _bp_exemplo()
    ind = indicadores_liquidez(bp)
    assert ind.liquidez_corrente == pytest.approx(2.0)
    assert ind.liquidez_seca == pytest.approx((200_000 - 50_000) / 100_000)
    assert ind.liquidez_imediata == pytest.approx(0.3)


def test_indicadores_endividamento():
    bp = _bp_exemplo()
    ind = indicadores_endividamento(bp)
    assert ind.endividamento_geral == pytest.approx(180_000 / 400_000)
    assert ind.composicao_endividamento == pytest.approx(100_000 / 180_000)


def test_indicadores_rentabilidade_e_ebitda():
    bp = _bp_exemplo()
    dre = DRE(
        receita_bruta=500_000,
        deducoes_receita=50_000,
        custo_produtos_vendidos=200_000,
        despesas_operacionais=100_000,
        resultado_financeiro=-5_000,
        depreciacao_amortizacao=20_000,
        irpj_csll=30_000,
    )
    assert dre.receita_liquida == pytest.approx(450_000)
    assert dre.lucro_bruto == pytest.approx(250_000)
    assert dre.lucro_operacional == pytest.approx(150_000)
    assert dre.ebitda == pytest.approx(170_000)

    ind = indicadores_rentabilidade(dre, bp)
    assert ind.margem_bruta == pytest.approx(250_000 / 450_000)
    assert ind.roe == pytest.approx(dre.lucro_liquido / bp.patrimonio_liquido)


def test_analise_vertical_e_horizontal():
    vertical = analise_vertical({"custo": 200_000, "despesas": 100_000}, base=500_000)
    assert vertical["custo"] == pytest.approx(0.4)

    horizontal = analise_horizontal(
        valores_periodo_atual={"receita": 550_000},
        valores_periodo_base={"receita": 500_000},
    )
    assert horizontal["receita"] == pytest.approx(0.10)


def test_dfc_calcula_variacao_e_caixa_final():
    dfc = DFC(
        fluxo_operacional=100_000,
        fluxo_investimento=-40_000,
        fluxo_financiamento=-10_000,
        caixa_inicial=20_000,
    )
    assert dfc.variacao_caixa == pytest.approx(50_000)
    assert dfc.caixa_final == pytest.approx(70_000)
