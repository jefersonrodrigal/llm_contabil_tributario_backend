"""Tabelas de alíquotas e parâmetros tributários.

Cada tabela carrega `vigencia_inicio` e `fonte` para que o sistema nunca
apresente um valor sem indicar desde quando e de onde ele vem. Verificado em
2026-11-03. Antes de confiar nestes valores em produção, reconfirme contra a
fonte oficial — alíquotas e tabelas são alteradas por lei/IN com frequência.
"""
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Faixa:
    limite_superior: float  # RBT12 (ou base) até onde esta faixa vale
    aliquota_nominal: float  # ex.: 0.04 = 4%
    parcela_deduzir: float


@dataclass(frozen=True)
class TabelaVersionada:
    vigencia_inicio: date
    fonte: str
    dados: dict


# ---------------------------------------------------------------------------
# Simples Nacional — Anexos I a V (LC 123/2006, redação da LC 155/2016).
# Faixas de RBT12 iguais para todos os anexos.
# ---------------------------------------------------------------------------
_FAIXAS_RBT12 = [180_000.0, 360_000.0, 720_000.0, 1_800_000.0, 3_600_000.0, 4_800_000.0]

_ANEXO_I = [
    Faixa(_FAIXAS_RBT12[0], 0.040, 0.0),
    Faixa(_FAIXAS_RBT12[1], 0.073, 5_940.0),
    Faixa(_FAIXAS_RBT12[2], 0.095, 13_860.0),
    Faixa(_FAIXAS_RBT12[3], 0.107, 22_500.0),
    Faixa(_FAIXAS_RBT12[4], 0.143, 87_300.0),
    Faixa(_FAIXAS_RBT12[5], 0.190, 378_000.0),
]

_ANEXO_II = [
    Faixa(_FAIXAS_RBT12[0], 0.045, 0.0),
    Faixa(_FAIXAS_RBT12[1], 0.078, 5_940.0),
    Faixa(_FAIXAS_RBT12[2], 0.100, 13_860.0),
    Faixa(_FAIXAS_RBT12[3], 0.112, 22_500.0),
    Faixa(_FAIXAS_RBT12[4], 0.147, 85_500.0),
    Faixa(_FAIXAS_RBT12[5], 0.300, 720_000.0),
]

_ANEXO_III = [
    Faixa(_FAIXAS_RBT12[0], 0.060, 0.0),
    Faixa(_FAIXAS_RBT12[1], 0.112, 9_360.0),
    Faixa(_FAIXAS_RBT12[2], 0.135, 17_640.0),
    Faixa(_FAIXAS_RBT12[3], 0.160, 35_640.0),
    Faixa(_FAIXAS_RBT12[4], 0.210, 125_640.0),
    Faixa(_FAIXAS_RBT12[5], 0.330, 648_000.0),
]

_ANEXO_IV = [
    Faixa(_FAIXAS_RBT12[0], 0.045, 0.0),
    Faixa(_FAIXAS_RBT12[1], 0.090, 8_100.0),
    Faixa(_FAIXAS_RBT12[2], 0.102, 12_420.0),
    Faixa(_FAIXAS_RBT12[3], 0.140, 39_780.0),
    Faixa(_FAIXAS_RBT12[4], 0.220, 183_780.0),
    Faixa(_FAIXAS_RBT12[5], 0.330, 828_000.0),
]

_ANEXO_V = [
    Faixa(_FAIXAS_RBT12[0], 0.155, 0.0),
    Faixa(_FAIXAS_RBT12[1], 0.180, 4_500.0),
    Faixa(_FAIXAS_RBT12[2], 0.195, 9_900.0),
    Faixa(_FAIXAS_RBT12[3], 0.205, 17_100.0),
    Faixa(_FAIXAS_RBT12[4], 0.230, 62_100.0),
    Faixa(_FAIXAS_RBT12[5], 0.305, 540_000.0),
]

SIMPLES_NACIONAL_ANEXOS = TabelaVersionada(
    vigencia_inicio=date(2018, 1, 1),
    fonte="LC 123/2006, art. 18 e Anexos I-V (redação da LC 155/2016)",
    dados={"I": _ANEXO_I, "II": _ANEXO_II, "III": _ANEXO_III, "IV": _ANEXO_IV, "V": _ANEXO_V},
)

SIMPLES_NACIONAL_LIMITE_RBT12 = 4_800_000.0
SIMPLES_NACIONAL_FATOR_R_CORTE = 0.28  # folha_12m / rbt12 >= 0.28 => Anexo III, senão Anexo V


# ---------------------------------------------------------------------------
# Lucro Presumido — percentuais de presunção (IN RFB nº 1.700/2017, art. 33).
# ---------------------------------------------------------------------------
LUCRO_PRESUMIDO_PERCENTUAIS = TabelaVersionada(
    vigencia_inicio=date(2017, 1, 1),
    fonte="IN RFB nº 1.700/2017, art. 33",
    dados={
        "comercio": {"irpj": 0.08, "csll": 0.12},
        "industria": {"irpj": 0.08, "csll": 0.12},
        "transporte_cargas": {"irpj": 0.08, "csll": 0.12},
        "transporte_passageiros": {"irpj": 0.16, "csll": 0.12},
        "servicos_hospitalares": {"irpj": 0.08, "csll": 0.12},
        "servicos_em_geral": {"irpj": 0.32, "csll": 0.32},
        "servicos_profissao_regulamentada": {"irpj": 0.32, "csll": 0.32},
        "revenda_combustiveis": {"irpj": 0.016, "csll": 0.12},
        "instituicoes_financeiras": {"irpj": 0.16, "csll": 0.12},
    },
)

# Acréscimo de 10% nos percentuais de presunção acima, vigente desde 2026,
# regulamentado pela IN RFB nº 2305/2025, art. 14-15 (com a redação dada pela
# IN RFB nº 2306/2026), com base na LC nº 224/2025. Mecanismo real (art. 15,
# §§1º-4º): o limite anual de R$ 5.000.000,00 é distribuído em um limite
# proporcional de R$ 1.250.000,00 por trimestre; se a receita do trimestre
# ficar abaixo do limite, a diferença é somada ao limite dos trimestres
# seguintes (carryforward); se ultrapassar, o acréscimo de 10% incide só
# sobre o excedente ao limite disponível naquele trimestre. IRPJ majorado
# desde 1º/1/2026; CSLL majorada desde 1º/4/2026 — nesta implementação ambos
# são tratados com a mesma data de corte por simplicidade.
#
# NÃO implementado: a reconciliação anual do último trimestre (art. 15,
# §§5º-8º), que pode recalcular trimestres anteriores e gerar restituição —
# esse mecanismo é significativamente mais complexo (aloca proporcionalmente
# entre trimestres que excederam o limite) e não está coberto aqui. Ver
# `taxation/lucro_presumido.py`.
LUCRO_PRESUMIDO_MAJORACAO = TabelaVersionada(
    vigencia_inicio=date(2026, 1, 1),
    fonte="IN RFB nº 2305/2025, art. 15 (redação da IN RFB nº 2306/2026); LC nº 224/2025",
    dados={
        "limite_proporcional_trimestral": 1_250_000.0,
        "acrescimo_percentual": 0.10,
    },
)

# ---------------------------------------------------------------------------
# IRPJ/CSLL — regras comuns a Lucro Presumido e Lucro Real (Lei 9.249/1995,
# arts. 3º e 20; Lei 9.430/1996, art. 4º).
# ---------------------------------------------------------------------------
IRPJ_ALIQUOTA_BASE = 0.15
IRPJ_ADICIONAL_ALIQUOTA = 0.10
IRPJ_ADICIONAL_LIMITE_TRIMESTRAL = 60_000.0  # R$ 20.000/mês x 3
IRPJ_ADICIONAL_LIMITE_ANUAL = 240_000.0
CSLL_ALIQUOTA_GERAL = 0.09

# ---------------------------------------------------------------------------
# PIS/COFINS
# ---------------------------------------------------------------------------
PIS_COFINS_CUMULATIVO = {"pis": 0.0065, "cofins": 0.03}  # regra geral do Lucro Presumido
PIS_COFINS_NAO_CUMULATIVO = {"pis": 0.0165, "cofins": 0.076}  # regra geral do Lucro Real

# ---------------------------------------------------------------------------
# Reforma Tributária — fase de testes 2026 (LC 214/2025, arts. 343 e 346).
# Alíquotas simbólicas, sem impacto na carga tributária líquida (valores
# recolhidos são compensados/ressarcidos). Não se aplica ao Simples Nacional.
# ---------------------------------------------------------------------------
REFORMA_TRIBUTARIA_FASE_TESTE_2026 = TabelaVersionada(
    vigencia_inicio=date(2026, 1, 1),
    fonte="LC 214/2025, art. 343 (IBS) e art. 346 (CBS)",
    dados={
        "cbs_aliquota": 0.009,
        "ibs_aliquota_estadual": 0.001,
        "ibs_aliquota_municipal": 0.0,
        "aplica_simples_nacional": False,
        "observacao": (
            "Alíquotas-teste de 2026, sem efeito na carga tributária líquida: "
            "valores são compensados com PIS/COFINS/ICMS devidos ou ressarcidos. "
            "Cronograma de 2027 em diante depende de regulamentação adicional "
            "(ex.: LC 227/2026) — consultar fonte antes de assumir vigência."
        ),
    },
)
