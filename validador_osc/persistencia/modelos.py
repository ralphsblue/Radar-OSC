import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CONVENCAO_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_NOMES)


class RespostaFonte(Base):
    __tablename__ = "resposta_fonte"
    __table_args__ = (
        CheckConstraint("resultado IN ('OBTIDO', 'NAO_ENCONTRADO', 'FALHA')", name="resultado"),
        Index(
            "ix_resposta_fonte_cache",
            "fonte",
            "chave",
            text("recebida_em DESC"),
            postgresql_where=text("resultado <> 'FALHA'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    fonte: Mapped[str] = mapped_column(Text)
    chave: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    resultado: Mapped[str] = mapped_column(Text)
    motivo_falha: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    recebida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duracao_ms: Mapped[int] = mapped_column(Integer)
    tentativas: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(Text)
    corpo: Mapped[bytes | None] = mapped_column(LargeBinary)
    sha256: Mapped[str | None] = mapped_column(String(64))


class Carga(Base):
    __tablename__ = "carga"
    __table_args__ = (
        CheckConstraint(
            "status IN ('EM_ANDAMENTO', 'CONCLUIDA', 'SEM_MUDANCA', 'FALHOU')",
            name="status",
        ),
        Index("uq_carga_fonte_ativa", "fonte", unique=True, postgresql_where=text("ativa")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    fonte: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    ativa: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    referencia: Mapped[str | None] = mapped_column(Text)
    data_base: Mapped[date | None] = mapped_column(Date)
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    url: Mapped[str] = mapped_column(Text)
    arquivo_caminho: Mapped[str | None] = mapped_column(Text)
    arquivo_sha256: Mapped[str | None] = mapped_column(String(64))
    arquivo_bytes: Mapped[int | None] = mapped_column(BigInteger)
    linhas: Mapped[int | None] = mapped_column(Integer)
    erro: Mapped[str | None] = mapped_column(Text)


class Consulta(Base):
    __tablename__ = "consulta"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CNPJ_INVALIDO', 'INAPTA', 'INCONCLUSIVA', 'APTA_COM_RESSALVAS', 'APTA')",
            name="status",
        ),
        CheckConstraint("esfera IN ('municipio', 'estado', 'uniao')", name="esfera"),
        Index("ix_consulta_cnpj_iniciada_em", "cnpj", text("iniciada_em DESC")),
        Index(
            "uq_consulta_chave_idempotencia",
            "chave_idempotencia",
            unique=True,
            postgresql_where=text("chave_idempotencia IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    cnpj_informado: Mapped[str] = mapped_column(Text)
    cnpj: Mapped[str] = mapped_column(String(14))
    cnpj_matriz: Mapped[str | None] = mapped_column(String(14))
    esfera: Mapped[str | None] = mapped_column(Text)
    data_referencia: Mapped[date] = mapped_column(Date)
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duracao_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)
    resultado: Mapped[dict[str, Any]] = mapped_column(JSONB)
    versao_app: Mapped[str] = mapped_column(Text)
    versao_regras: Mapped[str] = mapped_column(Text)
    forcou_atualizacao: Mapped[bool] = mapped_column(Boolean)
    chave_idempotencia: Mapped[str | None] = mapped_column(Text)


class ConsultaEvidencia(Base):
    __tablename__ = "consulta_evidencia"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(resposta_fonte_id, carga_id) = 1",
            name="origem_unica",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    consulta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consulta.id", ondelete="CASCADE"), index=True)
    resposta_fonte_id: Mapped[int | None] = mapped_column(ForeignKey("resposta_fonte.id"), index=True)
    carga_id: Mapped[int | None] = mapped_column(ForeignKey("carga.id"), index=True)
    papel: Mapped[str] = mapped_column(Text)
    de_cache: Mapped[bool] = mapped_column(Boolean)
