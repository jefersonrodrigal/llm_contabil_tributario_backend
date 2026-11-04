"""Estrutura da Demonstração do Resultado do Exercício (DRE), conforme Lei
6.404/1976, art. 187."""
from pydantic import BaseModel


class DRE(BaseModel):
    receita_bruta: float
    deducoes_receita: float = 0.0  # impostos sobre vendas, devoluções, descontos
    custo_produtos_vendidos: float = 0.0
    despesas_operacionais: float = 0.0
    resultado_financeiro: float = 0.0  # positivo = receita financeira líquida
    depreciacao_amortizacao: float = 0.0
    irpj_csll: float = 0.0

    @property
    def receita_liquida(self) -> float:
        return self.receita_bruta - self.deducoes_receita

    @property
    def lucro_bruto(self) -> float:
        return self.receita_liquida - self.custo_produtos_vendidos

    @property
    def lucro_operacional(self) -> float:
        """EBIT — lucro antes do resultado financeiro e dos tributos sobre o lucro."""
        return self.lucro_bruto - self.despesas_operacionais

    @property
    def lucro_antes_ir_csll(self) -> float:
        return self.lucro_operacional + self.resultado_financeiro

    @property
    def lucro_liquido(self) -> float:
        return self.lucro_antes_ir_csll - self.irpj_csll

    @property
    def ebitda(self) -> float:
        return self.lucro_operacional + self.depreciacao_amortizacao
