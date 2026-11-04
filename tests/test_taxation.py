import pytest

from taxation.lucro_presumido import calcular_lucro_presumido
from taxation.lucro_real import calcular_lucro_real
from taxation.simples_nacional import calcular_das, determinar_anexo_servicos
from taxation.tax_reform import simular_ibs_cbs_teste_2026


def test_calcular_das_anexo_i_primeira_faixa():
    resultado = calcular_das(receita_mes=15_000, rbt12=150_000, anexo="I")
    assert resultado.faixa_indice == 1
    assert resultado.aliquota_nominal == pytest.approx(0.04)
    assert resultado.aliquota_efetiva == pytest.approx(0.04)
    assert resultado.valor_das == pytest.approx(600.0)


def test_calcular_das_anexo_i_quarta_faixa_aliquota_efetiva_menor_que_nominal():
    resultado = calcular_das(receita_mes=100_000, rbt12=1_000_000, anexo="I")
    assert resultado.faixa_indice == 4
    assert resultado.aliquota_efetiva < resultado.aliquota_nominal


def test_calcular_das_acima_do_limite_levanta_erro():
    with pytest.raises(ValueError):
        calcular_das(receita_mes=100_000, rbt12=5_000_000, anexo="I")


def test_fator_r_anexo_iii_quando_folha_alta():
    assert determinar_anexo_servicos(folha_12_meses=300_000, rbt12=1_000_000) == "III"


def test_fator_r_anexo_v_quando_folha_baixa():
    assert determinar_anexo_servicos(folha_12_meses=100_000, rbt12=1_000_000) == "V"


def test_lucro_presumido_servicos_gerais():
    resultado = calcular_lucro_presumido(receita_trimestre=300_000, atividade="servicos_em_geral")
    assert resultado.parcela_receita_majorada == 0.0
    assert resultado.base_presumida_irpj == pytest.approx(96_000)
    assert resultado.irpj == pytest.approx(14_400)
    assert resultado.irpj_adicional == pytest.approx((96_000 - 60_000) * 0.10)
    assert resultado.csll == pytest.approx(96_000 * 0.09)
    assert resultado.total_tributos > 0


def test_lucro_presumido_sem_majoracao_dentro_do_limite_trimestral():
    resultado = calcular_lucro_presumido(receita_trimestre=1_000_000, atividade="comercio")
    assert resultado.parcela_receita_majorada == 0.0
    assert resultado.saldo_limite_nao_utilizado == pytest.approx(250_000)


def test_lucro_presumido_majoracao_10pct_quando_excede_limite_trimestral():
    # Limite trimestral de R$ 1.250.000; receita de R$ 2.000.000 excede em R$ 750.000.
    resultado = calcular_lucro_presumido(receita_trimestre=2_000_000, atividade="comercio")
    assert resultado.parcela_receita_majorada == pytest.approx(750_000)
    assert resultado.saldo_limite_nao_utilizado == 0.0
    base_esperada = 1_250_000 * 0.08 + 750_000 * 0.08 * 1.10
    assert resultado.base_presumida_irpj == pytest.approx(base_esperada)


def test_lucro_presumido_saldo_nao_utilizado_carrega_para_proximo_trimestre():
    # Trimestre 1: receita baixa, sobra saldo. Trimestre 2: usa o saldo
    # carregado antes de aplicar o acréscimo de 10%.
    t1 = calcular_lucro_presumido(receita_trimestre=1_000_000, atividade="comercio")
    assert t1.saldo_limite_nao_utilizado == pytest.approx(250_000)

    t2 = calcular_lucro_presumido(
        receita_trimestre=1_400_000,
        atividade="comercio",
        saldo_limite_nao_utilizado_anterior=t1.saldo_limite_nao_utilizado,
    )
    # limite disponível no T2 = 1.250.000 + 250.000 = 1.500.000 >= 1.400.000
    assert t2.parcela_receita_majorada == 0.0
    assert t2.saldo_limite_nao_utilizado == pytest.approx(100_000)


def test_lucro_real_prejuizo_nao_gera_irpj_csll():
    resultado = calcular_lucro_real(lucro_real_trimestre=-50_000, receita_bruta_trimestre=200_000)
    assert resultado.irpj == 0.0
    assert resultado.csll == 0.0
    assert resultado.pis > 0  # PIS/COFINS incidem sobre receita, não sobre lucro


def test_simular_ibs_cbs_teste_2026_nao_aplica_simples():
    resultado = simular_ibs_cbs_teste_2026(valor_operacao=10_000, optante_simples=True)
    assert resultado.total_ibs_cbs == 0.0


def test_simular_ibs_cbs_teste_2026_regime_normal():
    resultado = simular_ibs_cbs_teste_2026(valor_operacao=10_000, optante_simples=False)
    assert resultado.cbs == pytest.approx(90.0)
    assert resultado.ibs_estadual == pytest.approx(10.0)
    assert resultado.total_ibs_cbs == pytest.approx(100.0)
