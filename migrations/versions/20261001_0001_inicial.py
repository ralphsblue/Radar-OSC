from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resposta_fonte",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("fonte", sa.Text(), nullable=False),
        sa.Column("chave", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("motivo_falha", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("recebida_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duracao_ms", sa.Integer(), nullable=False),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("corpo", sa.LargeBinary(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "resultado IN ('OBTIDO', 'NAO_ENCONTRADO', 'FALHA')", name=op.f("ck_resposta_fonte_resultado")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resposta_fonte")),
    )
    op.create_index(
        "ix_resposta_fonte_cache",
        "resposta_fonte",
        ["fonte", "chave", sa.literal_column("recebida_em DESC")],
        postgresql_where=sa.text("resultado <> 'FALHA'"),
    )

    op.create_table(
        "carga",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("fonte", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("ativa", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("referencia", sa.Text(), nullable=True),
        sa.Column("data_base", sa.Date(), nullable=True),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("arquivo_caminho", sa.Text(), nullable=True),
        sa.Column("arquivo_sha256", sa.String(length=64), nullable=True),
        sa.Column("arquivo_bytes", sa.BigInteger(), nullable=True),
        sa.Column("linhas", sa.Integer(), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('EM_ANDAMENTO', 'CONCLUIDA', 'SEM_MUDANCA', 'FALHOU')", name=op.f("ck_carga_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_carga")),
    )
    op.create_index(
        "uq_carga_fonte_ativa", "carga", ["fonte"], unique=True, postgresql_where=sa.text("ativa")
    )

    op.create_table(
        "consulta",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cnpj_informado", sa.Text(), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("cnpj_matriz", sa.String(length=14), nullable=True),
        sa.Column("esfera", sa.Text(), nullable=True),
        sa.Column("data_referencia", sa.Date(), nullable=False),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duracao_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("resultado", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("versao_app", sa.Text(), nullable=False),
        sa.Column("versao_regras", sa.Text(), nullable=False),
        sa.Column("forcou_atualizacao", sa.Boolean(), nullable=False),
        sa.Column("chave_idempotencia", sa.Text(), nullable=True),
        sa.CheckConstraint("esfera IN ('municipio', 'estado', 'uniao')", name=op.f("ck_consulta_esfera")),
        sa.CheckConstraint(
            "status IN ('CNPJ_INVALIDO', 'INAPTA', 'INCONCLUSIVA', 'APTA_COM_RESSALVAS', 'APTA')",
            name=op.f("ck_consulta_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consulta")),
    )
    op.create_index(
        "ix_consulta_cnpj_iniciada_em", "consulta", ["cnpj", sa.literal_column("iniciada_em DESC")]
    )
    op.create_index(
        "uq_consulta_chave_idempotencia",
        "consulta",
        ["chave_idempotencia"],
        unique=True,
        postgresql_where=sa.text("chave_idempotencia IS NOT NULL"),
    )

    op.create_table(
        "consulta_evidencia",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("consulta_id", sa.UUID(), nullable=False),
        sa.Column("resposta_fonte_id", sa.BigInteger(), nullable=True),
        sa.Column("carga_id", sa.BigInteger(), nullable=True),
        sa.Column("papel", sa.Text(), nullable=False),
        sa.Column("de_cache", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "num_nonnulls(resposta_fonte_id, carga_id) = 1", name=op.f("ck_consulta_evidencia_origem_unica")
        ),
        sa.ForeignKeyConstraint(
            ["carga_id"], ["carga.id"], name=op.f("fk_consulta_evidencia_carga_id_carga")
        ),
        sa.ForeignKeyConstraint(
            ["consulta_id"],
            ["consulta.id"],
            name=op.f("fk_consulta_evidencia_consulta_id_consulta"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resposta_fonte_id"],
            ["resposta_fonte.id"],
            name=op.f("fk_consulta_evidencia_resposta_fonte_id_resposta_fonte"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consulta_evidencia")),
    )
    op.create_index(op.f("ix_consulta_evidencia_carga_id"), "consulta_evidencia", ["carga_id"])
    op.create_index(op.f("ix_consulta_evidencia_consulta_id"), "consulta_evidencia", ["consulta_id"])
    op.create_index(
        op.f("ix_consulta_evidencia_resposta_fonte_id"), "consulta_evidencia", ["resposta_fonte_id"]
    )


def downgrade() -> None:
    op.drop_table("consulta_evidencia")
    op.drop_table("consulta")
    op.drop_table("carga")
    op.drop_table("resposta_fonte")
