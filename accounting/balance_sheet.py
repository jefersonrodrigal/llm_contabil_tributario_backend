"""Estrutura do Balanço Patrimonial, conforme Lei 6.404/1976, art. 178."""
from pydantic import BaseModel, model_validator


class BalancoPatrimonial(BaseModel):
    # Ativo
    ativo_circulante: float
    ativo_realizavel_longo_prazo: float = 0.0
    ativo_imobilizado: float = 0.0
    ativo_intangivel: float = 0.0
    ativo_investimentos: float = 0.0

    # Passivo
    passivo_circulante: float
    passivo_nao_circulante: float = 0.0

    # Patrimônio Líquido
    patrimonio_liquido: float

    # Decomposição opcional do ativo circulante, usada em alguns indicadores
    estoques: float = 0.0
    disponivel: float = 0.0  # caixa + equivalentes

    @property
    def ativo_nao_circulante(self) -> float:
        return (
            self.ativo_realizavel_longo_prazo
            + self.ativo_imobilizado
            + self.ativo_intangivel
            + self.ativo_investimentos
        )

    @property
    def ativo_total(self) -> float:
        return self.ativo_circulante + self.ativo_nao_circulante

    @property
    def passivo_total_exigivel(self) -> float:
        return self.passivo_circulante + self.passivo_nao_circulante

    @model_validator(mode="after")
    def valida_equacao_contabil(self) -> "BalancoPatrimonial":
        ativo = self.ativo_total
        passivo_pl = self.passivo_total_exigivel + self.patrimonio_liquido
        if abs(ativo - passivo_pl) > max(0.01, ativo * 1e-6):
            raise ValueError(
                f"Balanço não fecha: Ativo total ({ativo:,.2f}) != "
                f"Passivo + PL ({passivo_pl:,.2f})"
            )
        return self
