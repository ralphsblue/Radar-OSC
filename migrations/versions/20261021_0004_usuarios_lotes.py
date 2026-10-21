from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("email", name=op.f("uq_usuario_email")),
    )
    op.create_table(
        "lote",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("esfera", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("total_itens", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("esfera IN ('municipio', 'estado', 'uniao')", name=op.f("ck_lote_esfera")),
        sa.CheckConstraint("status IN ('PENDENTE', 'PROCESSANDO', 'CONCLUIDO')", name=op.f("ck_lote_status")),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_lote_usuario_id_usuario"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lote")),
    )
    op.create_index(
        "ix_lote_usuario_criado_em", "lote", ["usuario_id", sa.text("criado_em DESC")], unique=False
    )
    op.create_table(
        "lote_item",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cnpj_informado", sa.Text(), nullable=False),
        sa.Column("posicao", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("consulta_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDENTE', 'PROCESSANDO', 'CONCLUIDO', 'ERRO')", name=op.f("ck_lote_item_status")
        ),
        sa.ForeignKeyConstraint(
            ["lote_id"], ["lote.id"], name=op.f("fk_lote_item_lote_id_lote"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["consulta_id"], ["consulta.id"], name=op.f("fk_lote_item_consulta_id_consulta")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lote_item")),
    )
    op.create_index("ix_lote_item_lote_posicao", "lote_item", ["lote_id", "posicao"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lote_item_lote_posicao", table_name="lote_item")
    op.drop_table("lote_item")
    op.drop_index("ix_lote_usuario_criado_em", table_name="lote")
    op.drop_table("lote")
    op.drop_table("usuario")
