from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lista_tcu_registro",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("carga_id", sa.BigInteger(), nullable=False),
        sa.Column("lista", sa.Text(), nullable=False),
        sa.Column("tipo_registro", sa.Text(), nullable=False),
        sa.Column("documento", sa.Text(), nullable=True),
        sa.Column("raiz", sa.String(length=8), nullable=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("nome_normalizado", sa.Text(), nullable=False),
        sa.Column("cpf_meio", sa.String(length=6), nullable=True),
        sa.Column("cpf_dv_final", sa.String(length=2), nullable=True),
        sa.Column("processo", sa.Text(), nullable=True),
        sa.Column("acordao", sa.Text(), nullable=True),
        sa.Column("data_acordao", sa.Date(), nullable=True),
        sa.Column("data_transito", sa.Date(), nullable=True),
        sa.Column("data_final", sa.Date(), nullable=True),
        sa.Column("linha", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("cpf_dv_final ~ '^[0-9]{2}$'", name=op.f("ck_lista_tcu_registro_cpf_dv_final")),
        sa.CheckConstraint("cpf_meio ~ '^[0-9]{6}$'", name=op.f("ck_lista_tcu_registro_cpf_meio")),
        sa.CheckConstraint(
            "documento IS NULL OR (tipo_registro = 'CNPJ' AND documento !~ '^[0-9]{11}$')",
            name=op.f("ck_lista_tcu_registro_documento_sem_cpf"),
        ),
        sa.CheckConstraint(
            "lista IN ('INIDONEOS', 'CONTAS_IRREGULARES', 'INABILITADOS')",
            name=op.f("ck_lista_tcu_registro_lista"),
        ),
        sa.CheckConstraint(
            "tipo_registro IN ('CPF', 'CNPJ')", name=op.f("ck_lista_tcu_registro_tipo_registro")
        ),
        sa.ForeignKeyConstraint(
            ["carga_id"], ["carga.id"], name=op.f("fk_lista_tcu_registro_carga_id_carga"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lista_tcu_registro")),
    )
    op.create_index(
        "ix_lista_tcu_registro_carga_documento", "lista_tcu_registro", ["carga_id", "documento"], unique=False
    )
    op.create_index(
        "ix_lista_tcu_registro_carga_pessoa",
        "lista_tcu_registro",
        ["carga_id", "nome_normalizado", "cpf_meio"],
        unique=False,
    )
    op.create_index(
        "ix_lista_tcu_registro_carga_raiz", "lista_tcu_registro", ["carga_id", "raiz"], unique=False
    )
    op.create_table(
        "sancao_registro",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("carga_id", sa.BigInteger(), nullable=False),
        sa.Column("cadastro", sa.Text(), nullable=False),
        sa.Column("tipo_pessoa", sa.String(length=1), nullable=True),
        sa.Column("documento", sa.Text(), nullable=True),
        sa.Column("raiz", sa.String(length=8), nullable=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("nome_normalizado", sa.Text(), nullable=False),
        sa.Column("cpf_meio", sa.String(length=6), nullable=True),
        sa.Column("cpf_dv_final", sa.String(length=2), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("data_inicio", sa.Date(), nullable=True),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("orgao", sa.Text(), nullable=True),
        sa.Column("esfera", sa.Text(), nullable=True),
        sa.Column("uf", sa.Text(), nullable=True),
        sa.Column("abrangencia", sa.Text(), nullable=True),
        sa.Column("fundamentacao", sa.Text(), nullable=True),
        sa.Column("processo", sa.Text(), nullable=True),
        sa.Column("valor_multa", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("codigo_sancao", sa.Text(), nullable=True),
        sa.Column("origem_informacoes", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("convenio", sa.Text(), nullable=True),
        sa.Column("linha", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("cadastro IN ('CEPIM', 'CEIS', 'CNEP')", name=op.f("ck_sancao_registro_cadastro")),
        sa.CheckConstraint("cpf_dv_final ~ '^[0-9]{2}$'", name=op.f("ck_sancao_registro_cpf_dv_final")),
        sa.CheckConstraint("cpf_meio ~ '^[0-9]{6}$'", name=op.f("ck_sancao_registro_cpf_meio")),
        sa.CheckConstraint(
            "documento IS NULL OR (tipo_pessoa IS DISTINCT FROM 'F' AND documento !~ '^[0-9]{11}$')",
            name=op.f("ck_sancao_registro_documento_sem_cpf"),
        ),
        sa.CheckConstraint("tipo_pessoa IN ('J', 'F')", name=op.f("ck_sancao_registro_tipo_pessoa")),
        sa.ForeignKeyConstraint(
            ["carga_id"], ["carga.id"], name=op.f("fk_sancao_registro_carga_id_carga"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sancao_registro")),
    )
    op.create_index(
        "ix_sancao_registro_carga_documento", "sancao_registro", ["carga_id", "documento"], unique=False
    )
    op.create_index(
        "ix_sancao_registro_carga_pessoa",
        "sancao_registro",
        ["carga_id", "nome_normalizado", "cpf_meio"],
        unique=False,
    )
    op.create_index("ix_sancao_registro_carga_raiz", "sancao_registro", ["carga_id", "raiz"], unique=False)


def downgrade() -> None:
    op.drop_table("sancao_registro")
    op.drop_table("lista_tcu_registro")
