"""CONTRACT: remove a coluna legada 'cliente'

Fase final do padrão Expand-Contract. Só deve ser aplicada depois que:
  1. a aplicação já grava em primeiro_nome/sobrenome (dual write);
  2. o backfill já preencheu os registros antigos (python backfill.py).

Por segurança, repete o backfill em SQL antes de remover a coluna,
garantindo que nenhum dado seja perdido.

Revision ID: 003_contract_v3
Revises: 002_expand_contract_v2
Create Date: 2026-10-19 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003_contract_v3'
down_revision = '002_expand_contract_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rede de segurança: preenche o que ainda estiver nulo a partir de 'cliente'.
    op.execute("""
        UPDATE transacoes
        SET primeiro_nome = SUBSTR(TRIM(cliente), 1, INSTR(TRIM(cliente) || ' ', ' ') - 1),
            sobrenome = TRIM(SUBSTR(TRIM(cliente), INSTR(TRIM(cliente) || ' ', ' ') + 1))
        WHERE primeiro_nome IS NULL AND cliente IS NOT NULL
    """)
    op.execute("UPDATE transacoes SET primeiro_nome = 'Desconhecido' "
               "WHERE primeiro_nome IS NULL OR primeiro_nome = ''")
    op.execute("UPDATE transacoes SET sobrenome = '' WHERE sobrenome IS NULL")

    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.alter_column('primeiro_nome', existing_type=sa.TEXT, nullable=False)
        batch_op.alter_column('sobrenome', existing_type=sa.TEXT, nullable=False)
        batch_op.drop_column('cliente')


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.add_column(sa.Column('cliente', sa.TEXT, nullable=True))
        batch_op.alter_column('primeiro_nome', existing_type=sa.TEXT, nullable=True)
        batch_op.alter_column('sobrenome', existing_type=sa.TEXT, nullable=True)
    op.execute(
        "UPDATE transacoes "
        "SET cliente = TRIM(COALESCE(primeiro_nome, '') || ' ' || COALESCE(sobrenome, ''))"
    )
