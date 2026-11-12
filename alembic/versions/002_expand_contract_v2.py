"""EXPAND: adiciona primeiro_nome/sobrenome e deixa 'cliente' opcional

Fase 1 do padrão Expand-Contract. Depois desta migração:
  - a versão N-1 da aplicação (que só conhece 'cliente') continua funcionando;
  - a versão N (dual write) já pode gravar nos dois formatos;
  - o preenchimento dos registros antigos é feito por `python backfill.py`.

Revision ID: 002_expand_contract_v2
Revises: 001_initial_v1
Create Date: 2026-10-19 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002_expand_contract_v2'
down_revision = '001_initial_v1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.add_column(sa.Column('primeiro_nome', sa.TEXT, nullable=True))
        batch_op.add_column(sa.Column('sobrenome', sa.TEXT, nullable=True))
        batch_op.alter_column('cliente', existing_type=sa.TEXT, nullable=True)


def downgrade() -> None:
    op.execute(
        "UPDATE transacoes "
        "SET cliente = TRIM(COALESCE(primeiro_nome, '') || ' ' || COALESCE(sobrenome, '')) "
        "WHERE cliente IS NULL"
    )
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_column('primeiro_nome')
        batch_op.drop_column('sobrenome')
        batch_op.alter_column('cliente', existing_type=sa.TEXT, nullable=False)
