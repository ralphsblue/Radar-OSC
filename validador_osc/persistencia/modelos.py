import uuid
from datetime import date, datetime
from decimal import Decimal
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
    Numeric,
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


class SancaoRegistro(Base):
    __tablename__ = "sancao_registro"
    __table_args__ = (
        CheckConstraint("cadastro IN ('CEPIM', 'CEIS', 'CNEP')", name="cadastro"),
        CheckConstraint("tipo_pessoa IN ('J', 'F')", name="tipo_pessoa"),
        CheckConstraint(
            "documento IS NULL OR (tipo_pessoa IS DISTINCT FROM 'F' AND documento !~ '^[0-9]{11}$')",
            name="documento_sem_cpf",
        ),
        CheckConstraint("cpf_meio ~ '^[0-9]{6}$'", name="cpf_meio"),
        CheckConstraint("cpf_dv_final ~ '^[0-9]{2}$'", name="cpf_dv_final"),
        Index("ix_sancao_registro_carga_documento", "carga_id", "documento"),
        Index("ix_sancao_registro_carga_raiz", "carga_id", "raiz"),
        Index("ix_sancao_registro_carga_pessoa", "carga_id", "nome_normalizado", "cpf_meio"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    carga_id: Mapped[int] = mapped_column(ForeignKey("carga.id", ondelete="CASCADE"))
    cadastro: Mapped[str] = mapped_column(Text)
    tipo_pessoa: Mapped[str | None] = mapped_column(String(1))
    documento: Mapped[str | None] = mapped_column(Text)
    raiz: Mapped[str | None] = mapped_column(String(8))
    nome: Mapped[str] = mapped_column(Text)
    nome_normalizado: Mapped[str] = mapped_column(Text)
    cpf_meio: Mapped[str | None] = mapped_column(String(6))
    cpf_dv_final: Mapped[str | None] = mapped_column(String(2))
    categoria: Mapped[str | None] = mapped_column(Text)
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)
    orgao: Mapped[str | None] = mapped_column(Text)
    esfera: Mapped[str | None] = mapped_column(Text)
    uf: Mapped[str | None] = mapped_column(Text)
    abrangencia: Mapped[str | None] = mapped_column(Text)
    fundamentacao: Mapped[str | None] = mapped_column(Text)
    processo: Mapped[str | None] = mapped_column(Text)
    valor_multa: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    codigo_sancao: Mapped[str | None] = mapped_column(Text)
    origem_informacoes: Mapped[str | None] = mapped_column(Text)
    motivo: Mapped[str | None] = mapped_column(Text)
    convenio: Mapped[str | None] = mapped_column(Text)
    linha: Mapped[dict[str, Any]] = mapped_column(JSONB)


class ListaTcuRegistro(Base):
    __tablename__ = "lista_tcu_registro"
    __table_args__ = (
        CheckConstraint("lista IN ('INIDONEOS', 'CONTAS_IRREGULARES', 'INABILITADOS')", name="lista"),
        CheckConstraint("tipo_registro IN ('CPF', 'CNPJ')", name="tipo_registro"),
        CheckConstraint(
            "documento IS NULL OR (tipo_registro = 'CNPJ' AND documento !~ '^[0-9]{11}$')",
            name="documento_sem_cpf",
        ),
        CheckConstraint("cpf_meio ~ '^[0-9]{6}$'", name="cpf_meio"),
        CheckConstraint("cpf_dv_final ~ '^[0-9]{2}$'", name="cpf_dv_final"),
        Index("ix_lista_tcu_registro_carga_documento", "carga_id", "documento"),
        Index("ix_lista_tcu_registro_carga_raiz", "carga_id", "raiz"),
        Index("ix_lista_tcu_registro_carga_pessoa", "carga_id", "nome_normalizado", "cpf_meio"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    carga_id: Mapped[int] = mapped_column(ForeignKey("carga.id", ondelete="CASCADE"))
    lista: Mapped[str] = mapped_column(Text)
    tipo_registro: Mapped[str] = mapped_column(Text)
    documento: Mapped[str | None] = mapped_column(Text)
    raiz: Mapped[str | None] = mapped_column(String(8))
    nome: Mapped[str] = mapped_column(Text)
    nome_normalizado: Mapped[str] = mapped_column(Text)
    cpf_meio: Mapped[str | None] = mapped_column(String(6))
    cpf_dv_final: Mapped[str | None] = mapped_column(String(2))
    processo: Mapped[str | None] = mapped_column(Text)
    acordao: Mapped[str | None] = mapped_column(Text)
    data_acordao: Mapped[date | None] = mapped_column(Date)
    data_transito: Mapped[date | None] = mapped_column(Date)
    data_final: Mapped[date | None] = mapped_column(Date)
    linha: Mapped[dict[str, Any]] = mapped_column(JSONB)


class TcespRegistro(Base):
    __tablename__ = "tcesp_registro"
    __table_args__ = (Index("ix_tcesp_registro_carga_pessoa", "carga_id", "nome_normalizado"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    carga_id: Mapped[int] = mapped_column(ForeignKey("carga.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(Text)
    nome_normalizado: Mapped[str] = mapped_column(Text)
    cpf_inicio: Mapped[str] = mapped_column(String(3))
    cpf_fim: Mapped[str] = mapped_column(String(2))
    processo: Mapped[str | None] = mapped_column(Text)
    materia: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[str | None] = mapped_column(Text)
    data_transito: Mapped[date | None] = mapped_column(Date)
    exercicio: Mapped[str | None] = mapped_column(Text)
    linha: Mapped[dict[str, Any]] = mapped_column(JSONB)
