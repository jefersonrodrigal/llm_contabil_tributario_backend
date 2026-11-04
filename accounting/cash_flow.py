"""Estrutura da Demonstração dos Fluxos de Caixa (DFC), conforme CPC 03 (R2)
— fluxos classificados em atividades operacionais, de investimento e de
financiamento."""
from pydantic import BaseModel


class DFC(BaseModel):
    fluxo_operacional: float
    fluxo_investimento: float = 0.0
    fluxo_financiamento: float = 0.0
    caixa_inicial: float = 0.0

    @property
    def variacao_caixa(self) -> float:
        return self.fluxo_operacional + self.fluxo_investimento + self.fluxo_financiamento

    @property
    def caixa_final(self) -> float:
        return self.caixa_inicial + self.variacao_caixa
