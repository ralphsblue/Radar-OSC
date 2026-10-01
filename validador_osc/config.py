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
        "postgresql+psycopg://validador:validador@127.0.0.1:55432/validador"
    )
    user_agent: str = "validador-osc-ifsp/0.1 (projeto academico de extensao)"
    timeout_fonte_s: float = Field(default=12.0, gt=0)
    prazo_consulta_s: float = Field(default=20.0, gt=0)
    dir_arquivos: Path = Path("var/arquivos")
    token_operador: SecretStr | None = None
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
