from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class FormatoLog(StrEnum):
    CONSOLE = "console"
    JSON = "json"


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VOSC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://validador:validador@127.0.0.1:15432/validador"
    )
    user_agent: str = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
    timeout_fonte_s: float = Field(default=12.0, gt=0)
    prazo_consulta_s: float = Field(default=20.0, gt=0)
    timeout_banco_s: int = Field(default=5, ge=2)
    dir_arquivos: Path = Path("var/arquivos")
    timeout_download_s: float = Field(default=300.0, gt=0)
    token_operador: SecretStr | None = None
    jwt_segredo: SecretStr = SecretStr("altere-este-segredo-em-producao-0123456789")
    jwt_expiracao_min: int = Field(default=720, ge=1)
    redis_url: str = "redis://127.0.0.1:16379/0"
    fila_nome: str = "lotes"
    # Valor provisório, ainda não validado com uso real - fácil de ajustar depois.
    fila_concorrencia: int = Field(default=4, ge=1)
    limite_consultas_por_minuto: int = Field(default=10, ge=0)
    log_formato: FormatoLog = FormatoLog.CONSOLE
    log_nivel: str = "INFO"
    fuso: str = "America/Sao_Paulo"

    @property
    def zona(self) -> ZoneInfo:
        return ZoneInfo(self.fuso)

    @property
    def url_banco(self) -> str:
        return str(self.database_url)


@lru_cache(maxsize=1)
def obter_configuracao() -> Configuracao:
    return Configuracao()
