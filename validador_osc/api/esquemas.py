from pydantic import BaseModel, ConfigDict, Field

from validador_osc.dominio.consulta import Esfera


class PedidoConsultaApi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpj: str = Field(min_length=1, max_length=32)
    esfera: Esfera | None = None
    atualizar: bool = False


class PedidoLoteApi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpjs: str = Field(min_length=1)
    esfera: Esfera | None = None


class Problema(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
