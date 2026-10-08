from pydantic import BaseModel, ConfigDict, Field

from validador_osc.dominio.consulta import Esfera


class PedidoConsultaApi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpj: str = Field(min_length=1, max_length=32)
    esfera: Esfera | None = None
    atualizar: bool = False


class Problema(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
