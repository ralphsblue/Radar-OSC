from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tcesp_registro",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("carga_id", sa.BigInteger(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("nome_normalizado", sa.Text(), nullable=False),
        sa.Column("cpf_inicio", sa.String(length=3), nullable=False),
        sa.Column("cpf_fim", sa.String(length=2), nullable=False),
        sa.Column("processo", sa.Text(), nullable=True),
        sa.Column("materia", sa.Text(), nullable=True),
        sa.Column("origem", sa.Text(), nullable=True),
        sa.Column("data_transito", sa.Date(), nullable=True),
        sa.Column("exercicio", sa.Text(), nullable=True),
        sa.Column("linha", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["carga_id"], ["carga.id"], name=op.f("fk_tcesp_registro_carga_id_carga"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tcesp_registro")),
    )
    op.create_index(
        "ix_tcesp_registro_carga_pessoa", "tcesp_registro", ["carga_id", "nome_normalizado"], unique=False
    )


def downgrade() -> None:
    op.drop_table("tcesp_registro")
