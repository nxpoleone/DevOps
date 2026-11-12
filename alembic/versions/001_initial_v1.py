"""Schema Inicial v1

Revision ID: 001_initial_v1
Revises:
Create Date: 2026-10-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'transacoes',
        sa.Column('id_transacao', sa.TEXT, primary_key=True),
        sa.Column('cliente', sa.TEXT, nullable=False),
        sa.Column('cpf', sa.TEXT, nullable=False),
        sa.Column('idade', sa.INTEGER),
        sa.Column('valor_bruto', sa.REAL),
        sa.Column('valor_final', sa.REAL),
        sa.Column('status', sa.TEXT),
        sa.Column('motivo_rejeicao', sa.TEXT),
        sa.Column('data_processamento', sa.TIMESTAMP),
    )


def downgrade() -> None:
    op.drop_table('transacoes')
